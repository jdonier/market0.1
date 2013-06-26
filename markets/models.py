from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum, Count
from django.db.models import Q
from operator import __or__ as OR


class EventManager(models.Manager):
	def tradedVolume(self, event):
		markets=Market.objects.filter(event=event)
		volume=0
		for market in markets:
			volume+=Trade.objects.filter(market=market, isNull=False).aggregate(Sum('volume'))['volume__sum']
		return volume
		
class MarketManager(models.Manager):
	def openInterest(self, market):
		traders=Trader.objects.all()
		openInterest=0
		for trader in traders:
			a=Trade.objects.filter(Q(market=market)  & ((Q(trader1=trader) &  Q(side=1)) | (Q(trader2=trader) &  Q(side=-1)))).aggregate(Sum('volume'))['volume__sum']
			if a==None:
				a=0
			b=Trade.objects.filter(Q(market=market)  & ((Q(trader2=trader) &  Q(side=1)) | (Q(trader1=trader) &  Q(side=-1)))).aggregate(Sum('volume'))['volume__sum']
			if b==None:
				b=0
			openInterest+=abs(a-b)/2
		return openInterest
	def tradedVolume(self, market):
		volume=Trade.objects.filter(market=market, nullTrade=False).aggregate(Sum('volume'))['volume__sum']
		return volume
		

class TraderManager(models.Manager):
	def PNL(self, trader):
		PNL=Trader.objects.deposit(trader=trader)+Trader.objects.totalLockedPNL(trader=trader)+Trader.objects.totalMarkPNL(trader=trader)
		return PNL
	def deposit(self, trader):
		transfers=Transfer.objects.filter(Q(trader=trader))
		deposit=0
		for transfer in transfers:
			deposit+=transfer.type*transfer.volume
		return deposit	
	def lockedPNL(self, trader, event): # event settled
		markets=Market.objects.filter(event=event)
		a=Trade.objects.filter(Q(trader1=trader) & Q(market__in=markets)).aggregate(Sum('PNL'))['PNL__sum']
		b=Trade.objects.filter(Q(trader2=trader) & Q(market__in=markets)).aggregate(Sum('PNL'))['PNL__sum']
		if a==None:
			a=0
		if b==None:
			b=0
		PNL=a-b	
		return PNL	
	def totalLockedPNL(self, trader): # all events settled
		a=Trade.objects.filter(Q(trader1=trader)).aggregate(Sum('PNL'))['PNL__sum']
		b=Trade.objects.filter(Q(trader2=trader)).aggregate(Sum('PNL'))['PNL__sum']
		if a==None:
			a=0
		if b==None:
			b=0
		PNL=a-b	
		return PNL
	def markPNL(self, trader, event): # non settled events
		markets=Market.objects.filter(event=event)
		minPOs=1000000000000000
		maxPos=-1000000000000000
		for market in markets:
			minPos=min(minPOs, \
			Trade.objects.filter(Q(market=market) & ((Q(trader1=trader) & Q(side=1)) | (Q(trader2=trader) & Q(side=-1)))).aggregate(Sum('volume'))['volume__sum'] \
			-Trade.objects.filter(Q(market=market) & ((Q(trader1=trader) & Q(side=-1)) | (Q(trader2=trader) & Q(side=1)))).aggregate(Sum('volume'))['volume__sum'])
			maxPos=max(maxPOs, \
			Trade.objects.filter(Q(market=market) & ((Q(trader1=trader) & Q(side=1)) | (Q(trader2=trader) & Q(side=-1)))).aggregate(Sum('volume'))['volume__sum'] \
			-Trade.objects.filter(Q(market=market) & ((Q(trader1=trader) & Q(side=-1)) | (Q(trader2=trader) & Q(side=1)))).aggregate(Sum('volume'))['volume__sum'])
		if minPos>0:
			PNL1=minPos # PNL for hedged orders
			PNL2=0 # PNL for open orders
			for market in markets:
				pos=Trade.objects.filter(Q(market=market) & ((Q(trader1=trader) & Q(side=1)) | (Q(trader2=trader) & Q(side=-1)))).aggregate(Sum('volume'))['volume__sum'] \
				-Trade.objects.filter(Q(market=market) & ((Q(trader1=trader) & Q(side=-1)) | (Q(trader2=trader) & Q(side=1)))).aggregate(Sum('volume'))['volume__sum']
				avgPrice=Trader.objects.avgPrice(trader=trader, market=market, side=1)
				PNL1-=minPos*avgPrice
				PNL2+=(pos-minPos)*(Market.objects.price(market=market)-avgPrice)
			PNL=PNL1+PNL2	
		elif maxPos<0:
			PNL1=maxPos # PNL for hedged orders
			PNL2=0 # PNL for open orders
			for market in markets:
				pos=Trade.objects.filter(Q(market=market) & ((Q(trader1=trader) & Q(side=1)) | (Q(trader2=trader) & Q(side=-1)))).aggregate(Sum('volume'))['volume__sum'] \
				-Trade.objects.filter(Q(market=market) & ((Q(trader1=trader) & Q(side=-1)) | (Q(trader2=trader) & Q(side=1)))).aggregate(Sum('volume'))['volume__sum']
				avgPrice=Trader.objects.avgPrice(trader=trader, market=market, side=-1)
				PNL1-=maxPos*avgPrice
				PNL2+=(pos-maxPos)*(Market.objects.price(market=market)-avgPrice)	
			PNL=PNL1+PNL2	
		else:
			PNL=0 # only open orders
			for market in markets:
				pos=Trade.objects.filter(Q(market=market) & ((Q(trader1=trader) & Q(side=1)) | (Q(trader2=trader) & Q(side=-1)))).aggregate(Sum('volume'))['volume__sum'] \
				-Trade.objects.filter(Q(market=market) & ((Q(trader1=trader) & Q(side=-1)) | (Q(trader2=trader) & Q(side=1)))).aggregate(Sum('volume'))['volume__sum']
				if pos>0:
					avgPrice=Trader.objects.avgPrice(trader=trader, market=market, side=1)
				else:	
					avgPrice=Trader.objects.avgPrice(trader=trader, market=market, side=-1)
				PNL+=pos*(Market.objects.price(market=market)-avgPrice)
		return PNL	
	def totalMarkPNL(self, trader): # non settled events
		PNL=0
		for event in Event.objects.filter(Q(status=0)):
			PNL+=Trader.objects.markPNL(trader=trader, event=event)
		return PNL	
	def avgPrice(self, trader, market, side):		
		trades=Trade.objects.filter(Q(market=market) & ((Q(trader1=trader) & Q(side=side)) | (Q(trader2=trader) & Q(side=-1*side))))
		price=0
		volume=0
		for trade in trades:
			price+=trade.price*trade.volume
			volume+=trade.volume
		avgPrice=0	
		if volume>0:
			avgPrice=price/volume
		return avgPrice
	def avgPriceLimits(self, trader, market, side):		
		limits=Limit.objects.filter(Q(market=market) & Q(trader=trader) & Q(side=side))
		price=0
		volume=0
		for limit in limits:
			price+=limit.price*limit.volume
			volume+=limit.volume
		avgPrice=0	
		if volume>0:
			avgPrice=price/volume
		return avgPrice
	def potentialAvailableBalance(self, trader):
		events=Event.objects.filter(Q(status=0))
		available=Trader.objects.deposit(trader=trader)+Trader.objects.totalLockedPNL(trader=trader)
		risk=0
		for event in events:
			worstPNL=Trader.objects.potentialRiskEvent(trader=trader, event=event)		
			risk+=worstPNL
		available-=risk
		return available		
	def availableBalance(self, trader):
		events=Event.objects.filter(Q(status=0))
		available=Trader.objects.deposit(trader=trader)+Trader.objects.totalLockedPNL(trader=trader)
		risk=0
		for event in events:
			worstPNL=Trader.objects.riskEvent(trader=trader, event=event)		
			risk+=worstPNL
		available-=risk
		return available		
	def riskEvent(self, trader, event):
		worstPNL=1000000000000
		markets=Market.objects.filter(event=event)
		volumeBuy=[]
		volumeBuyLimits=[]
		volumeSell=[]
		volumeSellLimits=[]
		avgBuy=[]
		avgBuyLimits=[]
		avgSell=[]
		avgSellLimits=[]
		nbMarkets=markets.aggregate(Count('outcome'))['outcome__count']
		for market in markets:
			a=Trade.objects.filter(Q(market=market) & ((Q(trader1=trader) & Q(side=1)) | (Q(trader2=trader) & Q(side=-1)))).aggregate(Sum('volume'))['volume__sum']
			if a==None:
				a=0
			volumeBuy.append(a)
			a=Limit.objects.filter(Q(market=market) & Q(trader=trader) & Q(side=1)).aggregate(Sum('volume'))['volume__sum']
			if a==None:
				a=0
			volumeBuyLimits.append(a)
			a=Trade.objects.filter(Q(market=market) & ((Q(trader1=trader) & Q(side=-1)) | (Q(trader2=trader) & Q(side=1)))).aggregate(Sum('volume'))['volume__sum']
			if a==None:
				a=0
			volumeSell.append(a)
			a=Limit.objects.filter(Q(market=market) & Q(trader=trader) & Q(side=-1)).aggregate(Sum('volume'))['volume__sum']
			if a==None:
				a=0
			volumeSellLimits.append(a)			
			avgBuy.append(Trader.objects.avgPrice(trader=trader, market=market, side=1))
			avgBuyLimits.append(Trader.objects.avgPriceLimits(trader=trader, market=market, side=1))
			avgSell.append(Trader.objects.avgPrice(trader=trader, market=market, side=-1))
			avgSellLimits.append(Trader.objects.avgPriceLimits(trader=trader, market=market, side=-1))
		for i in range(0, nbMarkets):
			if nbMarkets>1:
				PNL=volumeBuy[i]*(1-avgBuy[i])-volumeSell[i]*(1-avgSell[i])-volumeSellLimits[i]*(1-avgSellLimits[i])
				for j in range(0, nbMarkets):
					if i<>j:
						PNL+=volumeSell[j]*avgSell[j]-volumeBuy[j]*avgBuy[j]-volumeBuyLimits[j]*avgBuyLimits[j]
				worstPNL=min(worstPNL, PNL)	
			else:
				worstPNL=volumeBuy[i]*(1-avgBuy[i])-volumeSell[i]*(1-avgSell[i])-volumeSellLimits[i]*(1-avgSellLimits[i])
				PNL=volumeSell[i]*avgSell[i]-volumeBuy[i]*avgBuy[i]-volumeBuyLimits[i]*avgBuyLimits[i]
				worstPNL=min(worstPNL, PNL)
		if event.status==1:
			worstPNL=0
		return -worstPNL
	def potentialRiskEvent(self, trader, event):	
		worstPNL=1000000000000
		markets=Market.objects.filter(event=event)
		volumeBuy=[]
		volumeSell=[]
		avgBuy=[]
		avgSell=[]
		nbMarkets=markets.aggregate(Count('outcome'))['outcome__count']
		for market in markets:
			volumeBuy.append(Trade.objects.filter(Q(market=market) & (Q(trader1=trader) & Q(side=1)) | (Q(trader2=trader) & Q(side=-1))).aggregate(Sum('volume'))['volume__sum'])
			volumeSell.append(Trade.objects.filter(Q(market=market) & (Q(trader1=trader) & Q(side=-1)) | (Q(trader2=trader) & Q(side=1))).aggregate(Sum('volume'))['volume__sum'])
			avgBuy.append(Trader.objects.avgPrice(trader=trader, market=market, side=1))
			avgSell.append(Trader.objects.avgPrice(trader=trader, market=market, side=-1))
		for i in range(0, nbMarkets):
			if nbMarkets>1:
				PNL=volumeBuy[i]*(1-avgBuy[i])-volumeSell[i]*(1-avgSell[i])
				for j in range(0, nbMarkets):
					if i<>j:
						PNL+=volumeSell[j]*avgSell[j]-volumeBuy[j]*avgBuy[j]
				worstPNL=min(worstPNL, PNL)	
			else:
				worstPNL=volumeBuy[i]*(1-avgBuy[i])-volumeSell[i]*(1-avgSell[i])
				PNL=volumeSell[i]*avgSell[i]-volumeBuy[i]*avgBuy[i]
				worstPNL=min(worstPNL, PNL)	
		if event.status==1:
			worstPNL=0
		return -worstPNL		
	def availableBalanceIf(self, trader, newIdMarket, newSide, newPrice, newVolume):
		events=Event.objects.filter(Q(status=0))
		available=Trader.objects.deposit(trader=trader)+Trader.objects.totalLockedPNL(trader=trader)
		risk=0
		for event in events:
			worstPNL=Trader.objects.riskEventIf(trader=trader, event=event, newIdMarket=newIdMarket, newSide=newSide, newPrice=newPrice, newVolume=newVolume)		
			risk+=worstPNL
		available-=risk
		return available		
	def riskEventIf(self, trader, event, newIdMarket, newSide, newPrice, newVolume):
		worstPNL=1000000000000
		markets=Market.objects.filter(event=event)
		volumeBuy=[]
		volumeBuyLimits=[]
		volumeSell=[]
		volumeSellLimits=[]
		avgBuy=[]
		avgBuyLimits=[]
		avgSell=[]
		avgSellLimits=[]
		nbMarkets=markets.aggregate(Count('outcome'))['outcome__count']
		for market in markets:
			a=Trade.objects.filter(Q(market=market) & ((Q(trader1=trader) & Q(side=1)) | (Q(trader2=trader) & Q(side=-1)))).aggregate(Sum('volume'))['volume__sum']
			if a==None:
				a=0
			volumeBuy.append(a)
			b=Limit.objects.filter(Q(market=market) & Q(trader=trader) & Q(side=1)).aggregate(Sum('volume'))['volume__sum']
			if b==None:
				b=0
			if newSide==1 and market.id==newIdMarket:
				b+=newVolume
				test=1
			volumeBuyLimits.append(b)
			c=Trade.objects.filter(Q(market=market) & ((Q(trader1=trader) & Q(side=-1)) | (Q(trader2=trader) & Q(side=1)))).aggregate(Sum('volume'))['volume__sum']
			if c==None:
				c=0
			volumeSell.append(c)
			d=Limit.objects.filter(Q(market=market) & Q(trader=trader) & Q(side=-1)).aggregate(Sum('volume'))['volume__sum']
			if d==None:
				d=0
			if newSide==-1 and market.id==newIdMarket:
				d+=newVolume
			volumeSellLimits.append(d)			
			avgBuy.append(Trader.objects.avgPrice(trader=trader, market=market, side=1))
			avgBuyLimits.append(Trader.objects.avgPriceLimitsIf(trader=trader, market=market, side=1, newIdMarket=newIdMarket, newSide=newSide, newPrice=newPrice, newVolume=newVolume))
			avgSell.append(Trader.objects.avgPrice(trader=trader, market=market, side=-1))
			avgSellLimits.append(Trader.objects.avgPriceLimitsIf(trader=trader, market=market, side=-1, newIdMarket=newIdMarket, newSide=newSide, newPrice=newPrice, newVolume=newVolume))
		for i in range(0, nbMarkets):
			if nbMarkets>1:
				PNL=volumeBuy[i]*(1-avgBuy[i])-volumeSell[i]*(1-avgSell[i])-volumeSellLimits[i]*(1-avgSellLimits[i])
				for j in range(0, nbMarkets):
					if i<>j:
						PNL+=volumeSell[j]*avgSell[j]-volumeBuy[j]*avgBuy[j]-volumeBuyLimits[j]*avgBuyLimits[j]
				worstPNL=min(worstPNL, PNL)	
			else:
				worstPNL=volumeBuy[i]*(1-avgBuy[i])-volumeSell[i]*(1-avgSell[i])-volumeSellLimits[i]*(1-avgSellLimits[i])
				PNL=volumeSell[i]*avgSell[i]-volumeBuy[i]*avgBuy[i]-volumeBuyLimits[i]*avgBuyLimits[i]
				worstPNL=min(worstPNL, PNL)
		if event.status==1:
			worstPNL=0
		return -worstPNL	
	def avgPriceLimitsIf(self, trader, market, side, newIdMarket, newSide, newPrice, newVolume):		
		limits=Limit.objects.filter(Q(market=market) & Q(trader=trader) & Q(side=side))
		price=0
		volume=0
		for limit in limits:
			price+=limit.price*limit.volume
			volume+=limit.volume
		if side==newSide and market.id==newIdMarket:
			price+=newPrice*newVolume
			volume+=newVolume
		avgPrice=0	
		if volume>0:
			avgPrice=price/volume
		return avgPrice
#class TradeManager(models.Manager):


class LimitManager(models.Manager):
	def limits(self, trader, market, side):
		limits=Limit.objects.filter(trader=trader, market=market, side=side).aggregate(Sum('volume'))['volume__sum']
		if limits==None:
			limits=0
		return limits

#class TransferManager(models.Manager):


#class OBHistoryManager(models.Manager):





class GlobalEvent(models.Model):
	title= models.CharField(max_length=255)
	dateClose = models.DateTimeField()
	
	def __unicode__(self):
           return self.title	

class Event(models.Model):
	globalEvent = models.ForeignKey(GlobalEvent)
	title= models.CharField(max_length=255)
	description = models.CharField(max_length=255)	
	status = models.IntegerField(default=0) #unsettled : 0, settled : 1
	dateCreation = models.DateTimeField(auto_now_add=True)
	creator = models.CharField(max_length=255)
	#objects=EventManager()
	
	def __unicode__(self):
           return self.title	
		   
class Market(models.Model):
	event = models.ForeignKey(Event)
	outcome = models.CharField(max_length=255)
	win = models.BooleanField() # Update when Event.status is set to 1
	objects=MarketManager()
	
	def __unicode__(self):
           return self.outcome	
		   
class Trader(models.Model):
	user = models.OneToOneField(User) 
	active=models.BooleanField(default=True)
	objects=TraderManager()
	
	def __unicode__(self):
           return self.user.username	
		   
class Trade(models.Model):
	market = models.ForeignKey(Market)
	trader1 = models.ForeignKey(Trader, related_name='trader1')
	trader2 = models.ForeignKey(Trader, related_name='trader2')
	timestamp = models.DateTimeField(auto_now_add=True)
	side = models.IntegerField()  # buy side : 1  sell side : -1 
	price=models.DecimalField(max_digits=4, decimal_places=4)
	volume=models.DecimalField(max_digits=16, decimal_places=9)
	PNL=models.DecimalField(max_digits=16, decimal_places=9, default=0) # PNL of trader 1 - Update when Event.status is set to 1
	nullTrade=models.BooleanField() # When a trader trades with himself
	#objects=TradeManager()
	
	
		   
class Limit(models.Model):   # Delete when Event is closed
	market = models.ForeignKey(Market)
	trader = models.ForeignKey(Trader)
	timestamp = models.DateTimeField(auto_now_add=True)
	side = models.IntegerField() # buy side : 1  sell side : -1 
	price=models.DecimalField(max_digits=4, decimal_places=4) # in [0; 100]
	volume=models.DecimalField(max_digits=16, decimal_places=9)
	objects=LimitManager()
	

		   
class Transfer(models.Model):
	trader = models.ForeignKey(Trader)
	type= models.IntegerField()#credit : 1  debit : -1
	volume=models.DecimalField(max_digits=16, decimal_places=9, default=0)
	timestamp = models.DateTimeField(auto_now_add=True)
	
		   
class OBHistory(models.Model):

	def __unicode__(self):
           return self.id	
		   


