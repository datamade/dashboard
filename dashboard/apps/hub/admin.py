import os
from django.contrib import admin
from django.conf import settings
from django.core.cache import cache

from models import Contact, DataFormat, ElecData, Log, Office, Organization, State

### FIELDSET ###
ELEC_DATA_FIELDSET = (
    ('Data Source', {
        'fields':('organization','portal_link','direct_link', 'result_type', 'formats'),
        'classes': ('grp-collapse grp-closed',),
    }),
    ('Race Meta', {
        'fields':('state', ('start_date', 'end_date'), ('race_type', 'runoff_for'), 'absentee_and_provisional'),
        'classes': ('grp-collapse grp-closed',),
    }),
    ('Special Election', {
        'description': """Special elections are edge cases that we itemize. <br>If this is a special,
                          check the box and fill in the office. If it's a House race, include the District number 
                          as an integer or 'AL' for At-Large.""",
        'fields':(('special', 'office', 'district'),),
        'classes': ('grp-collapse grp-closed',),
    }),
    ('Office(s) Covered', {
        'description':'Data for this source includes results for:',
        'fields':(
            ('prez', 'senate', 'house', 'gov',),
            ('state_officers','state_leg',),
        ),
        'classes': ('grp-collapse grp-closed',),
    }),
    ('Reporting Level(s)', {
        'description':'Reporting levels at which results data are broken down. Racewide is the common case and denotes the widest jurisdiction '
                      'or reporting level at which data are available. In the case of presidential, senate or gubernatorial races, '
                      '"Racewide" implies statewide; in the case of U.S. House races, "Racewide" implies district-wide results.<br><br>' 
                      'The Congressional District and State Legislative boxes should only be flagged when there are result breakdowns ' 
                      'at those levels for unrelated offices. In other words, flag the Congressional District box if there are results for the '
                      'presidential race at the congressional district level. Do NOT check the box to denote results for a U.S. House race '
                      '(these should be denoted with the "Racewide" checkbox).',
        'fields':(
            ('state_level', 'county_level', 'precinct_level'),
            ('cong_dist_level', 'state_leg_level',),
            'level_note'
        ),
        'classes': ('grp-collapse grp-closed',),
    }),
    ('Notes', {
        'fields':('note',),
        'classes': ('grp-collapse grp-closed',),
    }),
)

### ADMIN CLASSES ###

class DataFormatAdmin(admin.ModelAdmin):
    list_display = ('name',)
    prepopulated_fields = {'slug':('name',)}

class ContactAdmin(admin.ModelAdmin):
    pass

class OfficeAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug':('name',)}

class ContactInline(admin.StackedInline):
    #TODO: Add custom validation to ensure that at least one form
    # of contact info has been entered (phone, mobile, email_work, email_personal)
    model = Contact
    extra = 0

class OrganizationAdmin(admin.ModelAdmin):
    #TODO: Add check to ensure that if gov agency is checked, 
    # gov_level must also be selected and vice versa 
    list_display = ('name', 'state',)
    list_display_link = ('url',)
    list_filter = ('gov_level', 'gov_agency',)
    prepopulated_fields = {'slug':('name',)}
    save_on_top = True
    inlines = [
        ContactInline,
    ]

    fieldsets = (
        (None, {
            'fields':(
                ('name', 'slug',),
                ('gov_agency', 'gov_level',),
                ('url', 'fec_page',),
            ),
        }),
        ('Address', {
            'fields':('street','city','state',),
        }),
        ('Profile', {
            'description':"<p>Notes on data sources, key contacts, etc.<p>",
            'fields':('description',),
        }),
    )

class ElecDataInline(admin.StackedInline):
    #TODO: validation rule - to ensure district only filled out for special elections
    #TODO: validation rule -  If special election, enforce that Offices covered only checked for appropriate office and no others
    #TODO: js helper - Create JS copy button that lets you populate values of new inline using values of a previous inline
    model = ElecData
    extra = 0
    filter_horizontal = ['formats']
    prepopulated_fields = {'end_date':('start_date',)}
    fieldsets = ELEC_DATA_FIELDSET

    def queryset(self, request):
        return super(ElecDataInline, self).queryset(request).prefetch_related('formats')

    def formfield_for_dbfield(self, db_field, **kwargs):
        formfield = super(ElecDataInline, self).formfield_for_dbfield(db_field, **kwargs)
        if db_field.name in set(['office', 'organization', 'formats']):
            # Force queryset evaluation and cache in .choices
            formfield.choices = formfield.choices
        return formfield

class LogInline(admin.StackedInline):
    model = Log
    extra = 0

class StateAdmin(admin.ModelAdmin):
    list_display = ['name']
    inlines = [
        ElecDataInline,
        LogInline,
    ]
    readonly_fields = ('name',)
    fieldsets = (
        (None, {
            'fields':('name', 'note',)
        }),
    )

    def save_formset(self, request, form, formset, change):
        if formset.model in (ElecData, Log):
            instances = formset.save(commit=False)
            for instance in instances:
                instance.user = request.user
                instance.save()
            formset.save_m2m()
        else:
            formset.save()

class ElecDataAdmin(admin.ModelAdmin):
    #TODO: dynamic attribute filter - create dynamic attribute that captures P/S/H/G -- ie core data -- for filter list
    model = ElecData
    filter_horizontal = ['formats']
    list_display = ['id', 'state', 'start_date', 'end_date', 'race_type', 'special', 'offices']
    list_display_links = ['id']
    save_on_top = True
    list_filter = [
        'start_date',
        'race_type',
        'runoff_for',
        'special',
        'office',
        'state',
        'result_type',
        'state_level',
        'county_level',
        'precinct_level',
        'prez',
        'senate',
        'house',
        'gov',
        'state_officers',
        'state_leg',
    ]
    fieldsets = ELEC_DATA_FIELDSET

    def save_model(self, request, obj, form, change):
        obj.user = request.user
        obj.save()

    def offices(self, obj):
        if obj.special:
            return obj.special_key(as_string=True)
        return ', '.join(obj.offices)
    offices.short_description = "Office(s) up for election"

admin.site.register(Contact, ContactAdmin)
admin.site.register(DataFormat, DataFormatAdmin)
admin.site.register(ElecData, ElecDataAdmin)
admin.site.register(Office, OfficeAdmin)
admin.site.register(Organization, OrganizationAdmin)
admin.site.register(State, StateAdmin)
