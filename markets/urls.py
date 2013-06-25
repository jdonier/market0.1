from django.conf.urls import patterns, url
from django.conf.urls.defaults import *

urlpatterns = patterns('markets.views',
	url(r'^$', 'home', name='home'),
	url(r'^signup/$', 'signup', name='signup'),
	url(r'^signin/$', 'signin', name='signin'),
	url(r'^signout/$', 'signout', name='signout'),
	url(r'^market/(?P<idMarket>\d+)/$', 'market', name='market'),
	url(r'^event/(?P<idEvent>\d+)/$', 'event', name='event'),
	url(r'^event/(?P<idEvent>\d+)/(?P<page>\d+)/$', 'event', name='eventList'),
	url(r'^globalevent/(?P<idgEvent>\d+)/$', 'globalEvent', name='globalEvent'),
	url(r'^globalevent/(?P<idgEvent>\d+)/(?P<page>\d+)/$', 'globalEvent', name='globalEventList'),
	url(r'^globalevents/$', 'allGlobalEvents', name='allGlobalEvents'),
	url(r'^globalevents/(?P<page>\d+)$', 'allGlobalEvents', name='allGlobalEventsList'),
	url(r'^createglobalevent/$', 'createGlobalEvent', name='createGlobalEvent'),
	url(r'^createevent/(?P<idgEvent>\d+)/$', 'createEvent', name='createEvent'),
	url(r'^createmarket/(?P<idEvent>\d+)/$', 'createMarket', name='createMarket'),
	url(r'^contact/$', 'contact'),
	url(r'^help/$', 'help'),
	url(r'^about/$', 'about'),
)