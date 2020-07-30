# -*- coding: utf-8 -*-
"""
Created on Tue Oct 22 16:06:06 2019

module: universal module - contains all the core input data - usually held constant/doesn't change between regions or farms'


Version Control:
Version     Date        Person  Change
1.1         25Dec19     John    structure['phase_len'] = 5 (rather than 4)
1.2         27Dec19     MRY     moved rotation input data from crop to here
1.3         13Jan20     MRY     changed input.py to universal - and added other bits such as price, interest rates and mach options
1.4         24Feb20     MRY     Added the capital set names to the set definition - this is required to build the pasture germination df without to many loops

Known problems:
Fixed   Date    ID by   Problem
1.2     25Dec19 John    The phase description in inputs are the full word whereas in the rotation phase it is just the letter.

@author: young
"""

##python modules
import pickle as pkl
import pandas as pd
import numpy as np
import datetime
from dateutil.relativedelta import relativedelta

import Functions as fun


#########################################################################################################################################################################################################
#########################################################################################################################################################################################################
#read in excel
#########################################################################################################################################################################################################
#########################################################################################################################################################################################################
import os.path
try:
    if os.path.getmtime("Universal.xlsx") > os.path.getmtime("pkl_universal.pkl"):
        inputs_from_pickle = False 
    else: 
        inputs_from_pickle = True
        print( 'Reading universal inputs from pickle')
except FileNotFoundError:      
    inputs_from_pickle = False

filename= 'pkl_universal.pkl'
##if inputs are not read from pickle then they are read from excel and written to pickle
if inputs_from_pickle == False:
    with open(filename, "wb") as f:
        ##prices
        price_inp = fun.xl_all_named_ranges("Universal.xlsx","Price")
        pkl.dump(price_inp, f)
        
        ##Finance inputs
        finance_inp = fun.xl_all_named_ranges("Universal.xlsx","Finance")
        pkl.dump(finance_inp, f)
        
        ##mach inputs - general
        mach_general_inp = fun.xl_all_named_ranges("Universal.xlsx","Mach General")
        pkl.dump(mach_general_inp, f)
        
        ##feed inputs
        feed_inputs_inp = fun.xl_all_named_ranges("Universal.xlsx","Feed Budget")
        pkl.dump(feed_inputs_inp, f)
        
        ##sup inputs
        sup_inp = fun.xl_all_named_ranges("Universal.xlsx","Sup Feed")
        pkl.dump(sup_inp, f)
        
        ##crop inputs
        crop_inp = fun.xl_all_named_ranges("Universal.xlsx","Crop Sim")
        pkl.dump(crop_inp, f)
        
        ##sheep inputs
        genotype_inp = fun.xl_all_named_ranges('Universal.xlsx', ['Genotypes'])
        pkl.dump(genotype_inp, f)
        parameters_inp = fun.xl_all_named_ranges('Inputs parameters.xlsm', ['Parameters'], numpy=True, datatype=float) #dtype included so that blank cells in excel get nan rather than NoneType. NoneType cant be mulitplied or added etc but nan can be.
        pkl.dump(parameters_inp, f)
        
        ##mach options
        ###create a dict to store all options - this allows the user to select an option
        machine_options_dict_inp={}
        machine_options_dict_inp[1] = fun.xl_all_named_ranges("Universal.xlsx","Mach 1")
        pkl.dump(machine_options_dict_inp, f)

##else the inputs are read in from the pickle file
##note this must be in the same order as above
else:
    with open(filename, "rb") as f:
        price_inp = pkl.load(f)
        
        finance_inp = pkl.load(f)
        
        mach_general_inp = pkl.load(f)
        
        feed_inputs_inp = pkl.load(f)
        
        sup_inp = pkl.load(f)
        
        crop_inp = pkl.load(f)
        
        genotype_inp = pkl.load(f)
        
        parameters_inp = pkl.load(f)
        
        machine_options_dict_inp  = pkl.load(f)
        
        
        
price = price_inp.copy()
finance = finance_inp.copy()
mach_general = mach_general_inp.copy()
feed_inputs = feed_inputs_inp.copy()
supfeed = sup_inp.copy()
crop = crop_inp.copy()
genotype = genotype_inp.copy()
parameters = parameters_inp.copy()
mach = machine_options_dict_inp.copy()

#######################
#apply SA             #
#######################
def univeral_inp_sa():
    '''
    
    Returns
    -------
    None.
    
    Applies sensitivity adjustment to each input.
    This function gets called at the beginning of each loop in the exp.py module

    '''
    ##have to import it here since sen.py imports this module
    import Sensitivity as sen 
    ##enter sa below
    
    
    

#########################################################################################################################################################################################################
#########################################################################################################################################################################################################
#general - used to determine model structure (these will stay in python to keep seperate from excel inputs which can be adjusted by any user)
#########################################################################################################################################################################################################
#########################################################################################################################################################################################################

##create an empty dict to store all structure inputs
structure = dict()

###############
# crop        #
###############
##grain pools there is one transfer constraint for each pool.
structure['grain_pools']=['firsts','seconds']

###############
# cashflow    #
###############
##the number of these can change as long as each period is of equal length.
structure['cashflow_periods']=['JF$FLOW','MA$FLOW','MJ$FLOW','JA$FLOW','SO$FLOW','ND$FLOW']

###############
# pasture     #
###############
##define which pastures are to be included
structure['pastures'] = ['annual'] # ,'lucerne','tedera']
structure['dry_groups'] = ['L', 'H']                       # Low & high quality groups for dry feed
structure['grazing_int'] =  ['0%', '25%', '75%', '100%']   # grazing intensity in the growth/grazing activities
structure['foo_levels'] =  ['L', 'M', 'H']                 # Low, medium & high FOO level in the growth/grazing activities

#######
#sheep#
#######
##pools
structure['sheep_pools']=['pool1', 'pool2', 'pool3', 'pool4']
structure['i_oldest_animal'] = 6.6
structure['n_sim_periods_year'] = 52 
##genotype
structure['i_mul_g0_k0'] = np.array([[1,0,0],
                                     [0,1,0],
                                     [0,0,1]])    
structure['i_mul_g1_k0'] = np.array([[1,   0,    0],
                                     [0.5,  0.5,  0]])    
structure['i_mul_g2_k0'] = np.array([[1,   0,    0],
                                     [0.5,  0.5,  0],
                                     [0.5,  0,    0.5],
                                     [0.25, 0.25, 0.5]])    
structure['i_mul_g3_k0'] = np.array([[1,   0,    0],
                                     [0.5,  0.5,  0],
                                     [0.5,  0,    0.5],
                                     [0.25, 0.25, 0.5]])    
structure['i_mask_g0g3'] = np.array([[True,True,True,True],
                                     [False,True,False,True],
                                     [False,False,True,True]])    
structure['i_mask_g1g3'] = np.array([[True,True,True,True],
                                     [False,False,False,True]])   
structure['i_mask_g2g3'] = np.array([[True,True,True,True],
                                     [False,True,False,True],
                                     [False,False,True,False],
                                     [False,False,False,True]])    
structure['i_mask_g3g3'] = np.array([[True,True,True,True],
                                    [False,True,False,True],
                                    [False,False,True,False],
                                    [False,False,False,True]])  
##variations between initial patterns
structure['i_w_pos'] = -10
structure['i_adjp_lw_initial_w0'] = np.array([0])        
structure['i_adjp_lw_initial_w1'] = np.array([0, 0.15, -0.15])        
structure['i_adjp_lw_initial_w3'] = np.array([0, 0.20, 0.10, -0.10, -0.20])        
###cfw
structure['i_adjp_cfw_initial_w0'] = np.array([0])        
structure['i_adjp_cfw_initial_w1'] = np.array([0, 0.05, -0.05])        
structure['i_adjp_cfw_initial_w3'] = np.array([0, 0.10, 0.05, -0.05, -0.10])        
###fd
structure['i_adjp_fd_initial_w0'] = np.array([0])        
structure['i_adjp_fd_initial_w1'] = np.array([0, 0.15, -0.15])        
structure['i_adjp_fd_initial_w3'] = np.array([0, 0.20, 0.10, -0.10, -0.20])        
###fl
structure['i_adjp_fl_initial_w0'] = np.array([0])        
structure['i_adjp_fl_initial_w1'] = np.array([0, 0.10, -0.10])        
structure['i_adjp_fl_initial_w3'] = np.array([0, 0.15, 0.08, -0.08, -0.15])        

########################
#period                #
########################
##Length of standard labour period, must be an integer that 12 is divisible by
structure['labour_period_len'] = relativedelta(months=1)


##############
#phases      #
##############
##the number of previous land uses considered for crop inputs - when this changes yeild input and fert and chem will need to be expended to include the extra years previous land use
structure['num_prev_phase']=1

#number of phases analysed ie rotation length if you will (although not really a rotation)
structure['phase_len'] = 6

#rotation phases and constraints read in from excel 
structure['phases'] = pd.read_excel('Rotation.xlsx', sheet_name='rotation list', header= None, index_col = 0).T.reset_index(drop=True).T  #reset the col headers to std ie 0,1,2 etc



###############
#landuses     #
###############
'''
A1, E1 are special sets used in con2 - currently not used
Note
- A1 is also used in pasture functions to build the germ df, so it cant be deleted
- C is used in stubble module, createmodel & mach
- C1 is used just in pasture functions
- sets now include capitals - this shouldnt effect con1 but it makes building the germ df easier
'''
##special sets that are used elsewhere from rotations
###used to make nap inputs - note cont lucerne and tedera are added seperately at the end of the cost section hence not inlcuded here.
structure['All_pas']={'a', 'ar', 'a3', 'a4', 'a5'
                , 's', 'sr', 's3', 's4', 's5'
                , 'm', 'm3', 'm4', 'm5'
                , 'u', 'ur', 'u3', 'u4', 'u5'
                , 'x', 'xr', 'x3', 'x4', 'x5'
                , 'j', 't', 'jr', 'tr'
                }
##next set is used in pasture.py for germination and phase area
structure['pasture_sets']={'annual': {'a', 'ar'
                                , 's', 'sr'
                                , 'm'}
                        ,'lucerne':{'u', 'uc', 'ur'
                                   , 'x', 'xc', 'xr'}
                        ,'tedera':{'j','jc', 't','tc', 'jr', 'tr'}
                       }
##G and C1 are just used in pas.py for germination ^can be removed when germination is calculated from sim
structure['G']={'b', 'h', 'o','of', 'w', 'f','i', 'k', 'l', 'v', 'z','r'
                , 'a', 'ar'
                , 's', 'sr'
                , 'm'
                , 'u', 'ur'
                , 'x', 'xr'
                , 'j', 't', 'jr', 'tr'
                , 'G', 'Y', 'E', 'N', 'P', 'OF'
                , 'A', 'AR'
                , 'S', 'SR'
                , 'M'
                , 'U'
                , 'X'
                , 'T', 'J'} #all landuses
structure['C1']={'E', 'N', 'P', 'OF', 'b', 'h', 'o', 'of', 'w', 'f','i', 'k', 'l', 'v', 'z','r'} #had to create a seperate set because don't want the capitatl in the crop set above as it is used to create pyomo set 


# structure['PAS_R']={'ar', 'sr', 'jr', 'tr', 'ur', 'xr', 'tc', 'jc', 'uc', 'xc'} #all reseeded pastures - used to determine pas sow 
structure['All']={'b', 'h', 'o', 'of', 'w', 'f','i', 'k', 'l', 'v', 'z','r', 'annual', 'tedera', 'lucerne'} #used in mach sow
structure['C']={'b', 'h', 'o', 'of', 'w', 'f','i', 'k', 'l', 'v', 'z','r'} #all crops, used in stubble and mach (not used for rotations)
structure['Hay']={'h'} #all crops that produce hay - used in machpyomo/coremodel for hay con
##special sets used in crop sim
structure['Ys'] = {'Y'}
structure['As'] = {'A','a'}
structure['JR'] = {'jr'}
structure['TR'] = {'tr'}
structure['UR'] = {'ur'}
structure['XR'] = {'xr'}
structure['PAS'] = {'A', 'AR', 'S', 'SR', 'M','T','J','U','X', 'tc', 'jc', 'uc', 'xc'} 
##sets used in to build rotations
structure['A']={'a', 'ar','s', 'sr', 'm'
                , 'A', 'AR'
                , 'S', 'SR'
                , 'M'} #annual
structure['A1']={'a',  's', 'm'} #annual not resown - special set used in pasture germ and con2 when determining if a rotatin provides a rotation because in yr1 we dont want ar to provide an A bevause we need to distinguish beteween them
structure['AR']={'ar', 'AR'} #resown annual
structure['E']={'E', 'E1', 'OF', 'b', 'h', 'o', 'of', 'w'} #cereals
structure['E1']={'E', 'b', 'h', 'o', 'w'} #cereals
# # structure['H']={'h', 'of'} #non harvested cereals
structure['J']={'J', 'j', 'jr'} #tedera
structure['M']={'m', 'M'} #manipulated pasture
structure['N']={'N', 'z','r'} #canolas
structure['OF']={'OF', 'of'} #oats fodder
structure['P']={'P', 'f','i', 'k', 'l', 'v'} #pulses
structure['S']={'s','sr', 'S', 'SR'} #spray topped pasture
structure['SR']={'sr', 'SR'} #spray topped pasture
structure['T']={'T', 't', 'tr','J', 'j', 'jr'} #tedera - also includes manipulated tedera because it is combined in yrs 3,4,5
structure['U']={'u', 'ur', 'U','x', 'xr', 'X'} #lucerne
structure['X']={'x', 'xr', 'X'} #lucerne
structure['Y']={'b', 'h', 'o','of', 'w', 'f','i', 'k', 'l', 'v', 'z','r'
                , 'Y', 'E', 'E1', 'N', 'P', 'OF'} #anything not pasture


'''make each landuse a set so the issuperset func works'''
structure['a']={'a'}
structure['ar']={'ar'}
structure['b']={'b'}
structure['f']={'f'}
structure['h']={'h'}
structure['i']={'i'}
structure['j']={'j'}
structure['jc']={'jc'}
structure['jr']={'jr'}
structure['k']={'k'}
structure['l']={'l'}
structure['m']={'m'}
structure['o']={'o'}
structure['of']={'of'}
structure['r']={'r'}
structure['s']={'s'}
structure['sr']={'sr'}
structure['t']={'t'}
structure['tc']={'tc'}
structure['tr']={'tr'}
structure['u']={'u'}
structure['uc']={'uc'}
structure['ur']={'ur'}
structure['v']={'v'}
structure['w']={'w'}
structure['x']={'x'}
structure['xc']={'xc'}
structure['xr']={'xr'}
structure['z']={'z'}











# phases = phases[~(np.isin(phases[:,i], ['U'])&np.isin(phases[:,i+1], ['U4','U5','u4','u5']))] #only U or U3 ufter U
#     phases = phases[~(np.isin(phases[:,i], ['U3'])&np.isin(phases[:,i+1], ['U', 'U3','U5','u','ur','u3','u5']))] #pasture 4 muxt come ufter pasture 3
#     phases = phases[~(np.isin(phases[:,i], ['U4'])&np.isin(phases[:,i+1], ['U', 'U3','U4','u','ur','u3','u4']))] #pasture 5 muxt come ufter pasture 4
#     phases = phases[~(np.isin(phases[:,i], ['U5'])&np.isin(phases[:,i+1], ['U', 'U3','U4','u','ur','u3','u4']))] #pasture 5 muxt come ufter pasture 5
#     phases = phases[~(~np.isin(phases[:,i], ['U'])&np.isin(phases[:,i+1], ['U3','u3']))] #cant have U3 after anything except U
#     try:  #used for conditions that are concerned with more than two yrs
#         phases = phases[~(~np.isin(phases[:,i], ['U'])&np.isin(phases[:,i+2], ['U3','u3']))] #cant have U3 ufter unything except U U (this is the second part to the rule above)
#     except IndexError: pass
#     phases = phases[~(~np.isin(phases[:,i], ['U3'])&np.isin(phases[:,i+1], ['U4','u4']))] #cant have U4 after anything except U3
#     phases = phases[~(~np.isin(phases[:,i], ['U4'])&np.isin(phases[:,i+1], ['U5','u5']))] #cant have U5 after anything except U4
#     try:  #used for conditions that are concerned with more than two yrs
#         phases = phases[~(np.isin(phases[:,i], ['U'])&np.isin(phases[:,i+1], ['U'])&~np.isin(phases[:,i+2], ['U3','u3']))] #can only huve U3 ufter U U (huve uxed u double negitive here)
#     except IndexError: pass

#     ##Manipulated Lucerne
#     phases = phases[~(np.isin(phases[:,i], ['X'])&np.isin(phases[:,i+1], ['X4','X5','x4','x5']))] #only U or U3 ufter U
#     phases = phases[~(np.isin(phases[:,i], ['X3'])&np.isin(phases[:,i+1], ['X','X3','X5','x','xr','x3','x5']))] #pasture 4 muxt come ufter pasture 3
#     phases = phases[~(np.isin(phases[:,i], ['X4'])&np.isin(phases[:,i+1], ['X','X3','X4','x','xr','x3','x4']))] #pasture 5 muxt come ufter pasture 4
#     phases = phases[~(np.isin(phases[:,i], ['X5'])&np.isin(phases[:,i+1], ['X','X3','X4','x','xr','x3','x4']))] #pasture 5 muxt come ufter pasture 5
#     phases = phases[~(~np.isin(phases[:,i], ['X'])&np.isin(phases[:,i+1], ['X3','x3']))] #cant have U3 after anything except U
#     try:  #used for conditions that are concerned with more than two yrs
#         phases = phases[~(~np.isin(phases[:,i], ['X'])&np.isin(phases[:,i+2], ['X3','x3']))] #cant have U3 ufter unything except U U (this is the second part to the rule above)
#     except IndexError: pass
#     phases = phases[~(~np.isin(phases[:,i], ['X3'])&np.isin(phases[:,i+1], ['X4','x4']))] #cant have U4 after anything except U3
#     phases = phases[~(~np.isin(phases[:,i], ['X4'])&np.isin(phases[:,i+1], ['X5','x5']))] #cant have U5 after anything except U4
#     try:  #used for conditions that are concerned with more than two yrs
#         phases = phases[~(np.isin(phases[:,i], ['X'])&np.isin(phases[:,i+1], ['X'])&~np.isin(phases[:,i+2], ['X3','x3']))] #can only huve U3 ufter U U (huve uxed u double negitive here)
#     except IndexError: pass

# #Lucerne
#
#########################################################################################################################################################################################################
#########################################################################################################################################################################################################
#universal functions that use data from above
#########################################################################################################################################################################################################
#########################################################################################################################################################################################################


#Function that just uses inout inputs but is used in multiple other pre-calc modules
#defined here to limit imorting pre calc modules in other precalc modules
def cols():
    #this is used to make a list of the relevent column numbers used in merge function, to specify the columns that are being matched - it will change if inputs specifying number of phases changes
    cols = []
    for i in reversed(range(structure['num_prev_phase']+1)):
        cols.append(structure['phase_len']-1-i) 
    return cols


