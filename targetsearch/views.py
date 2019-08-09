from django.shortcuts import render
from django.http import HttpResponse
from lockdown.decorators import lockdown
from compounddb.models import Compound, Tag

from .chembl_helpers import (
    byActivity,
    byAnnotations,
    mapToChembl
    )

from django.conf import settings

import os
import csv

@lockdown()
def search(request):
    sourceDbs  = readSources()
    query_submit = False
    annotationMatches = None
    activityMatches = None
    message = None
    ids = ()
    search_type="compound"
    allTags = Tag.allUserTagNames(request.user)

    if 'id' in request.GET:
        search_type = request.GET['search_type']


        ids = tuple(request.GET['id'].split())

        print("ids: "+str(ids))
        if search_type == 'compound':
            print("doing compound search")
            source_id = request.GET['source_id']
            
            if 'tags' in request.GET:
                ids =ids + tuple( [compound.cid for compound in  Compound.byTagNames(request.GET.getlist("tags"),request.user)])

            try:
                if source_id != "1" : # not CHEMBL
                    print("mapping to source_id")
                    ids = mapToChembl(ids,source_id)


                if len(ids) > 0 :
                    query_submit = True
                    annotationMatches = byAnnotations(chemblIds=ids)
                    activityMatches = byActivity(chemblIds=ids)
                else:
                    message = "None of the given IDs could be converted to ChEMBL IDs"
            except Exception as e:
                print("failed to do compound search: "+str(e))
                message = e

        elif search_type == 'target':
            print("doing target search")
            query_submit = True
            annotationMatches = byAnnotations(accessionIds=ids)
            if 'include_activity' in request.GET:
                activityMatches = byActivity(accessionIds=ids)

    context = {
        'query_submit': query_submit,
        'ids': ids,
        'activityMatches': activityMatches,
        'annotationMatches':annotationMatches,
        'sources':sourceDbs,
        'message': message,
        'search_type':search_type,
        'tags':allTags,
        }

    #print("results: "+str(context))
    
    return render(request, 'targetsearch.html', context)


def readSources():
    sources = {}
    filename = os.path.join(settings.PROJECT_DIR,"unichem_sources.txt")
    with open(filename) as f:
        for line in f:
            (key, val) = line.split("\t")
            sources[int(key)] = val
    return sources




