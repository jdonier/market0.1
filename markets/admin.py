from django.contrib import admin
from django.contrib.auth.models import User
from markets.models import GlobalEvent, Event, Market, Trade, Limit, Trader, Transfer, OBHistory


admin.site.register(GlobalEvent)
admin.site.register(Event)
admin.site.register(Market)
admin.site.register(Trade)
admin.site.register(Limit)
admin.site.register(Trader)
admin.site.register(Transfer)
admin.site.register(OBHistory)