#-*- coding: utf-8 -*-
from django import forms
 
class SignupForm(forms.Form):
    username = forms.CharField(label="User Name", max_length=30, widget=forms.TextInput(attrs={'class': 'formField', 'placeholder': 'Username'}))
    email = forms.EmailField(label=u"Email", widget=forms.TextInput(attrs={'class': 'formField', 'placeholder': 'Email'}))
    password = forms.CharField(label="Password", widget=forms.PasswordInput(attrs={'class': 'formField', 'placeholder': 'Password'}))
	
class LoginForm(forms.Form):
    username = forms.CharField(label="Nom d'utilisateur", max_length=30, widget=forms.TextInput(attrs={'class': 'signinField', 'placeholder': 'Username'}))
    password = forms.CharField(label="Mot de passe", widget=forms.PasswordInput(attrs={'class': 'signinField', 'placeholder': 'Password'}))

class GlobalEventForm(forms.Form):
	title = forms.CharField(label="Title", max_length=30, widget=forms.TextInput(attrs={'class': 'formField', 'placeholder': 'Title'}))
	dateClose = forms.DateTimeField(label="Close date", widget=forms.TextInput(attrs={'class': 'formField', 'placeholder': 'Ex : 31/12/2013'}))
 
 
class EventForm(forms.Form):
	title = forms.CharField(label="Title", max_length=30, widget=forms.TextInput(attrs={'class': 'formField', 'placeholder': 'Title'}))
	description = forms.CharField(label="Description",  max_length=255, widget=forms.TextInput(attrs={'class': 'formField', 'placeholder': 'Description'}))
   
class MarketForm(forms.Form):
	outcome = forms.CharField(label="Outcome", max_length=255, widget=forms.TextInput(attrs={'class': 'formField', 'placeholder': 'Outcome'}))
	
	#def __init__(self, fields, *args, **kwargs):
	#	super(MarketForm, self).__init__(*args, **kwargs)
	#	for i in xrange(fields):
	#		self.fields['outcome_%i' % i] = forms.CharField(label="Outcome", max_length=255, widget=forms.TextInput(attrs={'class': 'formField', 'placeholder': 'Outcome'}))
			
class OrderForm(forms.Form):
    side = forms.ChoiceField(label="Type", choices=((1, "Buy"), (-1, "Sell")))
    price = forms.DecimalField(label="Price", max_digits=4, decimal_places=4, widget=forms.TextInput(attrs={'class': 'formField', 'placeholder': 'Ex : 0.4020'}))
    volume = forms.DecimalField(label="Volume", widget=forms.TextInput(attrs={'class': 'formField', 'placeholder': 'Ex : 1.5'}))
 
class TransferForm(forms.Form):
    type = forms.ChoiceField(label="Type", choices=((1, "Deposit"), (-1, "Withdraw")))
    volume = forms.DecimalField(label="Volume", widget=forms.TextInput(attrs={'class': 'formField'}))
 
 
 
 
'''
class SignupForm(forms.Form):
    name = forms.CharField(label="User Name", max_length=30, widget=forms.TextInput(attrs={'class': 'formField', 'placeholder': 'Username'}))
    email = forms.EmailField(label=u"Email", widget=forms.TextInput(attrs={'class': 'formField', 'placeholder': 'Email'}))
    pwd = forms.CharField(label="Password", widget=forms.PasswordInput(attrs={'class': 'formField', 'placeholder': 'Password'}))
	
class ConnexionForm(forms.Form):
    username = forms.CharField(label="Nom d'utilisateur", max_length=30, widget=forms.TextInput(attrs={'class': 'signinField', 'placeholder': 'Username'}))
    password = forms.CharField(label="Mot de passe", widget=forms.PasswordInput(attrs={'class': 'signinField', 'placeholder': 'Password'}))
	
	
class MarketForm(forms.Form):
    name = forms.CharField(label="Title", max_length=30)
    description = forms.CharField(label="Description",  max_length=255)
	
class TradeForm(forms.Form):
    type = forms.ChoiceField(label="Type", choices=((1, "Buy"), (0, "Sell")))
    price = forms.DecimalField(label="Price")
    volume = forms.DecimalField(label="Volume")
'''