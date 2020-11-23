# -*- coding: utf-8 -*-
"""
Created on Wed Nov 13 10:13:44 2019

Module - calcs for crop labour

@author: young
"""
#python modules
import pandas as pd
import numpy as np
import timeit

#MUDAS modules
# from LabourCropInputs import *
import Functions as fun
import Crop as crp
import Periods as per
import Mach as mac
import PropertyInputs as pinp
import UniversalInputs as uinp

########################
#phases                #
########################
##makes a df of all possible rotation phases
phases_df =uinp.structure['phases']


#########################
#pack and prep time     #
#########################
#this function just combines all the needed elements to call the dict_period_total function.
#what is happening; i have a number of dicts that contain dates and the number of hours of labour for that date
#i want to combine and end up with the total hours of work done for each labour period
def prep_labour(params):
    p_dates = per.p_date2_df()['date']
    #gets the period name 
    p_name = per.p_date2_df().index
    #list of all the dicts that i want to combine
    dfs=pinp.labour['harvest_prep'],pinp.labour['fert_prep'] \
    , pinp.labour['spray_prep'], pinp.labour['seed_prep']
    params['prep_labour'] = fun.df_period_total(p_dates, p_name, *dfs) # '*' used to unpack list into seperate items for func

###########################
#fert applicaation time   #  this is similar to app cost done in mach sheet
###########################
#this is split into two sections - new feature of midas
# 1- time to drive around 1ha
# 2- time per cubic metre ie to represent filling up and driving to and from paddock

#allocation of fert costs into each cash period for each fert ie depending on the date diff ferts are in diff cash periods
def lab_allocation():
    start_df = pinp.crop['fert_info']['app_date'] 
    length_df = pinp.crop['fert_info']['app_len'].astype('timedelta64[D]') 
    p_dates = per.p_dates_df()['date']
    p_name = per.p_dates_df().index
    return fun.period_allocation2(start_df, length_df, p_dates, p_name)


#time/per ha - needs to be multiplied by the number of phases and then added to phases df because the previous phases can effect number of passes and hence time
#also need to account for arable area
def fert_app_time_ha(params):
    ##fert passes - arable
    fert_passes = crp.f_fert_passes()
    ##arable proportion
    arable = pinp.crop['arable'].squeeze()
    ##adjust fert passes by arable area
    index = pd.MultiIndex.from_product([fert_passes.index, arable.index])
    fert_passes = fert_passes.reindex(index, axis=0,level=0)
    passes=fert_passes.mul(arable,axis=0,level=1)
    ##passes over non arable area (only for pasture phases becasue for pasture the non arable areas also recieve fert)
    passes_na = pinp.crop['nap_passes']
    passes_na= passes_na.mul(1-arable).T #adjust for the non arable area
    arr=[list(uinp.structure['All_pas']),list(passes_na.index)] #create multi index from lmu and pasture landuse code
    inx = pd.MultiIndex.from_product(arr)
    passes_na = passes_na.reindex(inx,axis=0,level=1)
    passes_na = pd.merge(phases_df2, passes_na.unstack(), how='left', left_on=uinp.cols()[-1], right_index = True) #merge with all the phases, requires because different phases have different application passes
    passes_na.drop(list(range(uinp.structure['phase_len'])), axis=1, level=0).stack([1]) #drop the segregated landuse cols
    ##combine arable and non arable passes
    total_passes = passes + passes_na


    ##adjust fert labour across each labour period
    time = lab_allocation().mul(mac.time_ha().squeeze()).stack() #time for 1 pass for each chem.
    ##adjust for passes
    time = total_passes.mul(time, axis=1,level=1) #total time
    time=time.sum(level=[0], axis=1).stack() #sum across fert type
    params['fert_app_time_ha'] = time.to_dict()  #add to precalc dict
#f=fert_app_time_ha()
#print(timeit.timeit(fert_app_time_ha,number=20)/20)

#time/t - need to convert m3 to tone and allocate into lab periods
def fert_app_time_t(params):
    spreader_proportion = pd.DataFrame([pinp.crop['fert_info']['spreader_proportion']])
    conversion = pd.DataFrame([pinp.crop['fert_info']['fert_density']])
    time = (mac.time_cubic() / conversion).mul(spreader_proportion.squeeze(),axis=1)
    params['fert_app_time_t'] = (time.iloc[0]*lab_allocation()).stack().to_dict()
#print(fert_app_time_t())    
    


###########################
#chem applicaation time   #  this is similar to app cost done in mach sheet
###########################

def chem_lab_allocation():
    '''
    Returns
    -------
    DataFrame
        Collates all the data needed then calls the allocation function, which returns \
        the allocation of labour for chem application into labour periods.
    '''
    start_df = pinp.crop['chem_info']['app_date'] 
    length_df = pinp.crop['chem_info']['app_len'].astype('timedelta64[D]') 
    p_dates = per.p_dates_df()['date']
    p_name = per.p_dates_df().index
    return fun.period_allocation2(start_df, length_df, p_dates, p_name)


def chem_app_time_ha(params):  
    '''
    Returns
    ----------
    Dict for pyomo
        Labour required by each rotation phase for spraying
    '''
    ##calc passes - this is a bit of a double up since it is also calced in crop.py but couldn't get a nice way to get it from there without splitting up the function and also requires crop to be imported.
    base_chem = np.load('Chem data.npy')
    chem_by_soil = pinp.crop['chem_by_lmu'] #read in chem by soil
    base_chem = pd.DataFrame(base_chem, index = phases_df.index, columns = chem_by_soil.index)
    ### adjust the chem cost for each rotation by lmu
    chem_by_soil1 = chem_by_soil.stack()
    chem=base_chem.mul(chem_by_soil1,axis=1,level=0)
    x = chem.to_numpy()
    step = pinp.crop['step_chem_passes'].reindex(chem.columns, axis=0,level=0).values.flatten() #reindex to account for lmu then convert to np
    chem_passes = fun.passes(x,step)
    chem_passes = pd.DataFrame(chem_passes, index = phases_df.index, columns = chem.columns) #turn it into df with correct indexes so it can be combined with cost allocation.
    ##adjust passes for arable area.
    arable = pinp.crop['arable'].squeeze()
    passes=chem_passes.mul(arable,axis=1,level=1).stack()
    ##adjust chem labour across each labour period
    time = chem_lab_allocation().mul(mac.spray_time_ha()).stack() #time for 1 pass for each chem.
    ##adjust for passes
    time = passes.mul(time, axis=1,level=1) #total time 
    time=time.sum(level=[0], axis=1).stack()
    params['chem_app_time_ha'] = time.to_dict()
    
# # t_chemlab=chem_app_time_ha()

    



















