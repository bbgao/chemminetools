#!/usr/bin/python

from builtins import str
import re
import time
#from string import join
from django.shortcuts import redirect, render
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from guest.decorators import guest_allowed, login_required
from django.template import RequestContext
from django.utils.http import urlunquote, urlquote
from tools.models import Application, Job
from tools.runapp import updateJob, createJob, getAppForm, parseToolForm
import tools
import eisearch
from sdftools.moleculeformats import smiles_to_sdf, sdf_to_sdf, \
    InputError, sdf_to_smiles
from eisearch import first_mol
import traceback
from compounddb.models import Compound, SDFFile,Tag
import csv
import functools

@guest_allowed
def search(request):
    application = Application.objects.get(name='EI Search')
    AppFormSet = getAppForm(application.id, request.user)
    if request.method != 'POST':
        smi = ''
        if 'smi' in request.GET:
            smi = str(request.GET['smi'])
            smi = urlunquote(smi)
        form = AppFormSet()
        allTags = Tag.allUserTagNames(request.user)
        return render(request,'search.html', dict(mode='form',
            smi=smi, form=form,
            tags=allTags))
    else:
        sdf = None
        smiles = None
        compid = u'query'
        if 'tags' in request.POST:
            givenTags = request.POST.getlist("tags")
            compoundList = Compound.byTagNames(givenTags,request.user)
            if len(compoundList) == 0:
                messages.error(request,"Error: No compounds found with selected tags")
            else:
                sdf = u''
                for compound in compoundList:
                    sdf = sdf + compound.sdffile_set.all()[0].sdffile.rstrip() + '\n'
                smiles = sdf_to_smiles(sdf)
        elif 'smiles' in request.POST:
            input_mode = 'smiles-input'
            sdf = u''
            try:
                smiles = request.POST['smiles']
                sdf = smiles_to_sdf(smiles)
            except:
                messages.error(request, 'Error: Invalid SMILES string!')
                sdf = None
        elif 'sdf' in request.FILES:
            input_mode = 'sdf-upload'
            try:
                sdf = request.FILES['sdf']
                sdf = first_mol(sdf.read())
                smiles = sdf_to_smiles(sdf)
            except:
                print(traceback.format_exc())
                messages.error(request, 'Invalid SDF!')
                sdf = None
        elif 'sdf' in request.POST:
            if 'draw' in request.POST:
                input_mode = 'draw'
                sdf = request.POST['sdf'] + '$$$$'
                try:
                    smiles = sdf_to_smiles(sdf)
                    smiles = re.match(r"^(\S+)", smiles).group(1)
                    smiles = smiles + ' ' + compid
                    sdf = smiles_to_sdf(smiles)
                except:
                    print(traceback.format_exc())
                    messages.error(request, 'Invalid drawing!')
                    sdf = None
            else:
                try:
                    input_mode = 'sdf-input'
                    sdf = first_mol(request.POST['sdf'])
                    smiles = sdf_to_smiles(sdf)
                except:
                    print(traceback.format_exc())
                    messages.error(request, 'Invalid input SDF!')
                    sdf = None
        form = AppFormSet(request.POST)
        if form.is_valid():
            commandOptions, optionsList = parseToolForm(form) 
        else:
            sdf = None
            messages.error(request, "Invalid form options!")
        if not sdf:
            print("no sdf found")
            return redirect(eisearch.views.search)
        smiles = re.search(r'(\S+)', smiles).group(1)
        smiles = urlquote(smiles)
        if request.POST['algorithm'] == u'fp':
            newJob = createJob(request.user, 'Fingerprint Search', optionsList, 
                               commandOptions, sdf, smiles)
        else:
            newJob = createJob(request.user, 'EI Search', optionsList, 
                               commandOptions, sdf, smiles)
        time.sleep(1)
        return redirect(tools.views.view_job, job_id=newJob.id,resource='')

@guest_allowed
def getStructures(request, job_id, format):

    # takes a search job ID and returns an SDF of the compounds from this result 

    try:
        job = updateJob(request.user, job_id)
        f = open(job.output, 'r')
        csvinput = csv.reader(f,delimiter=' ')
        #read each line, extrace the second column, and combine all values 
        #into a new-line separated string
        targetIds = "\n".join([line[1] for line in csvinput])
        print("targetIds: "+str(targetIds))
        f.close()
        #result = '\n'.join(re.findall(r'^\S+', result, re.MULTILINE))
    except Job.DoesNotExist:
        print(traceback.format_exc())
        raise Http404
    newJob = createJob(request.user, 'chemblID2SMILES', '', [], targetIds,
                       format, async=False) 
    if format == 'smiles':
        filename = 'search_result.smi'
    else:
        filename = 'search_result.sdf' 
    return redirect(tools.views.view_job, job_id=newJob.id,resource='other',filename=filename)
