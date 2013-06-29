#-*- coding: utf-8 -*-
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import redirect
from datetime import datetime
from decimal import *
from django.db.models import Q
from django.utils import timezone
from django.shortcuts import render, get_object_or_404
import string, random
from django.db import transaction
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout 
from django.core.paginator import Paginator, EmptyPage  # Ne pas oublier l'importation
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Avg, Max, Min, Sum, Count
from markets.forms import SignupForm, LoginForm, GlobalEventForm, EventForm, MarketForm, OrderForm, TransferForm
from markets.models import GlobalEvent, Event, Market, Trader, Trade, Limit, OBHistory, Transfer



@staff_member_required	
def unsettleEvent(request, idEvent):
	event=Event.objects.get(id=idEvent)
	event.status=0
	event.save()
	markets=Market.objects.filter(event=event)
	for market in markets:
		trades=Trade.objects.filter(market=market)
		for trade in trades:
			trade.PNL=0
			trade.save()
	return redirect(reverse(showEvent, kwargs={'idEvent':idEvent}))	

@staff_member_required	
def settleEvent(request, idEvent, idMarket):
	event=Event.objects.get(id=idEvent)
	event.status=1
	event.save()
	nbMarkets=Market.objects.filter(event=event).aggregate(Count('outcome'))['outcome__count']
	singleMarket=False
	if nbMarkets==1:
		singleMarket=True
		market=Market.objects.get(event=event)
		win=True
		if idMarket==0:
			win=False	
		market.win=win
		market.save()
		trades=Trade.objects.filter(market=market)
		for trade in trades:
			if (trade.side==1 and win==True): 
				trade.PNL=(1-trade.price)*trade.volume
			elif (trade.side==-1 and win==False):
				trade.PNL=trade.price*trade.volume
			elif (trade.side==1 and win==False):	
				trade.PNL=-trade.price*trade.volume
			elif (trade.side==-1 and win==True):	
				trade.PNL=-(1-trade.price)*trade.volume
			trade.save()	
	else:
		market=Market.objects.get(id=idMarket)
		market.win=True
		market.save()
		trades=Trade.objects.filter(market=market)
		for trade in trades:
			if trade.side==1:
				trade.PNL=(1-trade.price)*trades.volume
			else:
				trade.PNL=-(1-trade.price)*trade.volume
			trade.save()
		markets=Market.objects.filter(event=event)
		for market1 in markets:
			if market1<>market:
				market1.win=False
				market1.save()		
				trades=Trade.objects.filter(market=market1)
				for trade in trades:
					if trade.side==-1:
						trade.PNL=trade.price*trade.volume
					else:
						trade.PNL=-trade.price*trade.volume
					trade.save()
	return redirect(reverse(showEvent, kwargs={'idEvent':idEvent}))	
	

@transaction.commit_on_success	
def showMarket(request, idMarket):	
	from django.db import connection
	cursor = connection.cursor()
	form2 = LoginForm()
	titre="Market"
	deleted=''
	market=Market.objects.get(id=idMarket)
	event=market.event
	msgNb=0
	err=False
	settled=False
	if event.status==1:
		settled=True
		mwin='Lost'
		if market.win==True:
			mwin='Won'
	trader=Trader()
	if request.user.is_authenticated:
		trader=Trader.objects.get(user=request.user)
		idUser=trader.user.id
		if request.method == 'POST' and trader.active==True and event.status==0 and event.globalEvent.dateClose>timezone.now():
			oform = OrderForm(request.POST)
			if oform.is_valid():
				volume=oform.cleaned_data['volume']
				price=oform.cleaned_data['price']
				side=int(oform.cleaned_data['side'])
				if Trader.objects.availableBalanceIf(trader=trader, newIdMarket=market.id, newSide=side, newPrice=price, newVolume=volume)>=0:
					try:
						deleted=execute(market, trader, side, price, volume)
					except:
						msgNb=1
						err=True
				else:
					msgNb=1
					err=True	
		else:
			oform = OrderForm()
		deposit=Decimal(Trader.objects.deposit(trader=trader)).quantize(Decimal('.01'), rounding=ROUND_DOWN)
		available=Decimal(Trader.objects.availableBalance(trader=trader)).quantize(Decimal('.01'), rounding=ROUND_DOWN)
		risk=-Decimal(Trader.objects.riskEvent(trader=trader, event=market.event)).quantize(Decimal('.01'), rounding=ROUND_DOWN)
		myBuyVolume=Trade.objects.filter(Q(market=market) & ((Q(trader1=trader) & Q(side=1)) | (Q(trader2=trader) & Q(side=-1))) & Q(nullTrade=False)).aggregate(Sum('volume'))['volume__sum']		
		if myBuyVolume==None:
			myBuyVolume=0
		myBuyVolume=Decimal(myBuyVolume).quantize(Decimal('.01'), rounding=ROUND_DOWN)	
		mySellVolume=Trade.objects.filter(Q(market=market) & ((Q(trader1=trader) & Q(side=-1)) | (Q(trader2=trader) & Q(side=1))) & Q(nullTrade=False)).aggregate(Sum('volume'))['volume__sum']		
		if mySellVolume==None:
			mySellVolume=0
		mySellVolume=Decimal(mySellVolume).quantize(Decimal('.01'), rounding=ROUND_DOWN)	
		avgPriceSell=Decimal(Trader.objects.avgPrice(trader=trader, market=market, side=-1)).quantize(Decimal('.01'), rounding=ROUND_DOWN)
		avgPriceBuy=Decimal(Trader.objects.avgPrice(trader=trader, market=market, side=1)).quantize(Decimal('.01'), rounding=ROUND_DOWN)
		myBuyLimits = Limit.objects.filter(market=market, trader=trader, side=1).order_by('-timestamp')
		mySellLimits = Limit.objects.filter(market=market, trader=trader, side=-1).order_by('-timestamp')
	else:
		oform = TradeForm()	
	cursor.execute("SELECT price price, sum(volume) volume FROM markets_limit WHERE side=1 and market_id=%i GROUP BY price ORDER BY price DESC" % market.id)
	limitsBuy = dictfetchall(cursor)
	cursor.execute("SELECT price price, sum(volume) volume FROM markets_limit WHERE side=-1 and market_id=%i GROUP BY price ORDER BY price DESC" % market.id)
	limitsSell = dictfetchall(cursor)
	cursor.execute("SELECT price price, volume volume, side side, timestamp timestamp FROM markets_trade WHERE not nullTrade and market_id=%i ORDER BY timestamp DESC" % market.id)
	trades = dictfetchall(cursor)
	trades=trades[:20]
	buyVolume=Limit.objects.filter(market=market, side=1).aggregate(Sum('volume'))['volume__sum']
	if buyVolume==None:
		buyVolume=0
	buyVolume=Decimal(buyVolume).quantize(Decimal('.01'), rounding=ROUND_DOWN)
	sellVolume=Limit.objects.filter(market=market, side=-1).aggregate(Sum('volume'))['volume__sum']
	if sellVolume==None:
		sellVolume=0
	sellVolume=Decimal(sellVolume).quantize(Decimal('.01'), rounding=ROUND_DOWN)
	tradedVolume=Decimal(Market.objects.tradedVolume(market=market)).quantize(Decimal('.01'), rounding=ROUND_DOWN)
	if tradedVolume==None:
		tradedVolume=0
	openInterest=Decimal(Market.objects.openInterest(market=market)).quantize(Decimal('.01'), rounding=ROUND_DOWN)
	if msgNb==1:
		oform.non_field_errors="Not enough balance !"
	return render(request, 'markets/market.html', locals())

def cancelOrder(request, idLimit):
	limit=Limit.objects.get(id=idLimit)
	idMarket=limit.market.id
	limit.delete()
	return redirect(reverse(showMarket, kwargs={'idMarket':idMarket}))	

def cancelAll(request, idMarket, idUser, side):
	market=Market.objects.get(id=idMarket)
	user=User.objects.get(id=idUser)
	trader=Trader.objects.get(user=user)
	s=-1
	if int(side)==1:
		s=1
	limits=Limit.objects.filter(market=market, trader=trader,  side=s)
	for limit in limits:
		limit.delete()
	return redirect(reverse(showMarket, kwargs={'idMarket':idMarket}))
	
def showEvent(request, idEvent, page=1):	
	form2 = LoginForm()
	titre="Event"
	event=Event.objects.get(id=idEvent)
	markets=Market.objects.filter(event=event)
	paginator = Paginator(markets, 4)
	nbMarkets=Market.objects.filter(event=event).aggregate(Count('outcome'))['outcome__count']
	settled=(event.status==1)
	try:
		minis = paginator.page(page)
	except EmptyPage:
		minis = paginator.page(paginator.num_pages)
	return render(request, 'markets/event.html', locals())

def showGlobalEvent(request, idgEvent, page=1):	
	form2 = LoginForm()
	titre="Event"
	gEvent=GlobalEvent.objects.get(id=idgEvent)
	events=Event.objects.filter(globalEvent=gEvent)
	paginator = Paginator(events, 4)
	try:
		minis = paginator.page(page)
	except EmptyPage:
		minis = paginator.page(paginator.num_pages)
	return render(request, 'markets/globalEvent.html', locals())

def allGlobalEvents(request, page=1):
	form2 = LoginForm()	
	titre="All Events"
	gEvents=GlobalEvent.objects.all()
	paginator = Paginator(gEvents, 4)
	try:
		minis = paginator.page(page)
	except EmptyPage:
		minis = paginator.page(paginator.num_pages)
	return render(request, 'markets/allGlobalEvents.html', locals())
	
def deleteMarket(request, idMarket):
	market=Market.objects.get(id=idMarket)
	idEvent=market.event.id	
	market.delete()
	return redirect(reverse(showEvent, kwargs={'idEvent':idEvent}))	
	
def createMarket(request, idEvent):
	form2 = LoginForm()
	title="non"
	event=Event.objects.get(id=idEvent)
	markets=Market.objects.filter(event=event)
	if request.method == "POST":
		mform = MarketForm(request.POST)
		if mform.is_valid():
			#for i in range(0, event.nbMarkets):
			market=Market()
			market.event=event
			#market.outcome = mform.cleaned_data['outcome_%i' % i]
			market.outcome = mform.cleaned_data['outcome']
			market.save()
			mform = MarketForm()	
		return render(request, 'markets/createMarket.html', locals())	
	else:
		mform = MarketForm()	
		return render(request, 'markets/createMarket.html', locals())	

def deleteEvent(request, idEvent):
	event=Event.objects.get(id=idEvent)
	idgEvent=event.globalEvent.id	
	event.delete()
	return redirect(reverse(showGlobalEvent, kwargs={'idgEvent':idgEvent}))	
	
def createEvent(request, idgEvent):
	form2 = LoginForm()
	gEvent=GlobalEvent.objects.get(id=idgEvent)
	if request.method == "POST":
		eform = EventForm(request.POST)
		if eform.is_valid():
			event=Event()
			event.globalEvent=GlobalEvent.objects.get(id=idgEvent)
			event.title = eform.cleaned_data['title']
			event.description = eform.cleaned_data['description']
			event.creator=request.user.username
			event.save()
			return HttpResponseRedirect(reverse('markets.views.createMarket', args=(event.id,)))
		else:	
			return render(request, 'markets/createEvent.html', locals())	
	else:
		eform = EventForm()	
		return render(request, 'markets/createEvent.html', locals())	

def deleteGlobalEvent(request, idgEvent):
	gEvent=GlobalEvent.objects.get(id=idgEvent)
	gEvent.delete()
	return redirect(reverse(allGlobalEvents))	
	
def createGlobalEvent(request):
	form2 = LoginForm()
	if request.method == "POST":   
		geform = GlobalEventForm(request.POST)
		if geform.is_valid():
			gEvent=GlobalEvent()
			gEvent.title = geform.cleaned_data['title']
			gEvent.dateClose = geform.cleaned_data['dateClose']
			gEvent.save()
			return HttpResponseRedirect(reverse('markets.views.createEvent', args=(gEvent.id,)))	
		else:	
			return render(request, 'markets/createGlobalEvent.html', locals())	
	else:
		geform = GlobalEventForm()	
		return render(request, 'markets/createGlobalEvent.html', locals())	

def allTraders(request, page=1):
	form2 = LoginForm()	
	traders=Trader.objects.all()
	paginator = Paginator(traders, 10)
	try:
		minis = paginator.page(page)
	except EmptyPage:
		minis = paginator.page(paginator.num_pages)
	return render(request, 'markets/allTraders.html', locals())
	
@staff_member_required
def toggleActivateTrader(request, idUser):	
	user=User.objects.get(id=idUser)
	trader=Trader.objects.get(user=user)
	trader.active= not trader.active
	trader.save()
	return redirect(reverse(showTrader, kwargs={'idUser':idUser}))	
	
@login_required	
def showTrader(request, idUser):	
	user=User.objects.get(id=idUser)
	trader=Trader.objects.get(user=user)
	titre=u'{0}'.format(user.username)
	if trader.active:
		action='Deactivate'
	else:
		action='Activate'
	return render(request, 'markets/trader.html', locals())	
	
def signup(request):
	if request.method == "POST":   
		form = SignupForm(request.POST)
		if form.is_valid():
			user=User()
			user.username = form.cleaned_data['username']
			user.email = form.cleaned_data['email']
			user.set_password(form.cleaned_data['password'])
			user.save()
			trader=Trader(user=user)
			trader.save()
			user = authenticate(username=form.cleaned_data['username'], password=form.cleaned_data['password'])  #Nous vérifions si les données sont correctes
			login(request, user)
			#return redirect('posts.views.user', id_user=user.id)
			return redirect('markets.views.home')
	else:
		form2 = LoginForm()
		form = SignupForm()	
	return render(request, 'markets/signup.html', locals())	

def signin(request):
	error = False    
	form = LoginForm(request.POST)
	if form.is_valid():
		username = form.cleaned_data["username"]  # Nous récupérons le nom d'utilisateur
		password = form.cleaned_data["password"]  # … et le mot de passe
		user = authenticate(username=username, password=password)  #Nous vérifions si les données sont correctes
		if user:  # Si l'objet renvoyé n'est pas None
			login(request, user)  # nous connectons l'utilisateur
			if not Trader.objects.filter(user=user):
				trader=Trader(user=user)
				trader.save()
		else: #sinon une erreur sera affichée
			error = True
	return redirect('markets.views.home')

def home(request):	
	titre="Home"
	form2 = LoginForm()	
	if request.method == "POST" and request.user.is_authenticated:   
		trform = TransferForm(request.POST)
		if trform.is_valid():
			transfer=Transfer()
			transfer.trader=Trader.objects.get(user=request.user)
			transfer.type=trform.cleaned_data["type"]
			transfer.volume=trform.cleaned_data["volume"]
			transfer.save()			
			trform = TransferForm()	
			trform.non_field_errors="Transfer successful !"
		else:	
			trform = TransferForm()	
	else:	
		trform = TransferForm()			
	return render(request, 'markets/home.html', locals())


def contact(request):
	titre="Contact"
	form2 = LoginForm()
	return render(request, 'markets/contact.html', locals())	
	
	
def help(request):
	titre="Help"
	form2 = LoginForm()
	return render(request, 'markets/help.html', locals())	
	
def about(request):
	titre="About"
	form2 = LoginForm()
	return render(request, 'markets/about.html', locals())	


def signout(request):
	logout(request)
	return redirect('markets.views.home')


'''

	
def all_users(request, page=1):	
	titre="All Users"
	traders=Trader.objects.all()
	paginator = Paginator(traders, 4)
	try:
		minis = paginator.page(page)
	except EmptyPage:
		minis = paginator.page(paginator.num_pages)
	return render(request, 'posts/all_users.html', locals())	

@login_required	
def new_market(request):
    if request.method == 'POST':  # S'il s'agit d'une requête POST
        form = MarketForm(request.POST)  # Nous reprenons les données
 
        if form.is_valid():
			market=Market()
			market.name = form.cleaned_data['name']
			market.creator=request.user.username
			market.description = form.cleaned_data['description']
			market.save()
			return redirect('posts.views.market', id_market=market.id)
    else: # Si ce n'est pas du POST, c'est probablement une requête GET
        form = MarketForm()  # Nous créons un formulaire vide
 
    return render(request, 'posts/new_market.html', locals())
	
	
		
	
@login_required	
def market(request, id_market):	
	from django.db import connection
	market=Market.objects.get(id=id_market)
	titre=u'{0}'.format(market.name)
	trader=Trader()
	if request.user.is_authenticated:
		trader=Trader.objects.get(user=request.user)
		if request.method == 'POST':
			form = TradeForm(request.POST)
			if form.is_valid():
				volume=form.cleaned_data['volume']
				price=form.cleaned_data['price']
				type=form.cleaned_data['type']
				if volume<=Trader.objects.balance(id_user=request.user.id):
					execute(market, trader, type, price, volume)
		else:
			form = TradeForm()
		available=Trader.objects.balance(id_user=request.user.id)		
	limits=Trade.objects.alllimits(id_market=market.id)
	buyVol=limits[1]
	buySell=limits[0]
	cursor = connection.cursor()	
	cursor.execute("SELECT price price, sum(volume) volume FROM posts_trade WHERE type=1 GROUP BY price ORDER BY price DESC")
	buyOrders = dictfetchall(cursor)
	cursor = connection.cursor()	
	cursor.execute("SELECT price price, sum(volume) volume FROM posts_trade WHERE type=0 GROUP BY price ORDER BY price DESC")
	sellOrders = dictfetchall(cursor)
	return render(request, 'posts/show_market.html', locals())	
	

'''	

def dictfetchall(cursor):
    "Returns all rows from a cursor as a dict"
    desc = cursor.description
    return [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]

def execute(market, trader, side, price, volume):
	volToExec=volume
	while side==1 and volToExec>0	and Limit.objects.filter(market=market, side=-1).aggregate(Min('price'))["price__min"]<>None and Limit.objects.filter(market=market, side=-1).aggregate(Min('price'))["price__min"]<=price:
		priceMin=Limit.objects.filter(market=market, side=-1).aggregate(Min('price'))["price__min"]
		timestampMin=Limit.objects.filter(market=market, price=priceMin, side=-1).aggregate(Min('timestamp'))["timestamp__min"]
		order=Limit.objects.get(market=market, price=priceMin, timestamp=timestampMin, side=-1)
		if order.volume<=volToExec:
			trade=Trade(market=market, trader1=trader, trader2=order.trader, side=1, price=order.price, volume=order.volume, nullTrade=(trader==order.trader)) 
			volInt=order.volume
			volToExec-=volInt
			trade.save()
			if Trader.objects.availableBalance(trader=trader)>=0:
				order.delete();
			else:	
				trade.delete()
		else:
			trade=Trade(market=market, trader1=trader, trader2=order.trader, side=1, price=order.price, volume=volToExec, nullTrade=(trader==order.trader)) 
			order.volume-=volToExec	
			volToExec=0
			trade.save()
			if Trader.objects.availableBalance(trader=trader)>=0:
				order.save();
			else:	
				trade.delete()
			
	while side==-1 and volToExec>0 and Limit.objects.filter(market=market, side=1).aggregate(Max('price'))["price__max"]<>None and Limit.objects.filter(market=market, side=1).aggregate(Max('price'))["price__max"]>=price:
		priceMax=Limit.objects.filter(market=market, side=1).aggregate(Max('price'))["price__max"]
		timestampMin=Limit.objects.filter(market=market, price=priceMax, side=1).aggregate(Min('timestamp'))["timestamp__min"]
		order=Limit.objects.get(market=market, price=priceMax, timestamp=timestampMin, side=1)	
		if order.volume<=volToExec:
			trade=Trade(market=market, trader1=trader, trader2=order.trader, side=-1, price=order.price, volume=order.volume, nullTrade=(trader==order.trader))
			volInt=order.volume
			volToExec-=volInt
			trade.save()
			if Trader.objects.availableBalance(trader=trader)>=0:
				order.delete();
			else:	
				trade.delete()
		else:
			trade=Trade(market=market, trader1=trader, trader2=order.trader, side=-1, price=order.price, volume=volToExec, nullTrade=(trader==order.trader)) 
			order.volume-=volToExec	
			order.save()		
			volToExec=0
			trade.save()
			if Trader.objects.availableBalance(trader=trader)>=0:
				order.save();
			else:	
				trade.delete()
			
	#Crée un limit order sur ce qui reste	
	deleted=''
	if volToExec>0:
		limit=Limit(market=market, trader=trader, side=side, price=price, volume=volToExec)
		limit.save()
		if Trader.objects.availableBalance(trader=trader)<0:
			limit.delete()
			return 'deleted'