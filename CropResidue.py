"""
author: young
"""
#python modules
import numpy as np

import pandas as pd
pd.set_option('mode.chained_assignment', 'raise')

#AFO modules
import Functions as fun
import SeasonalFunctions as zfun
import FeedsupplyFunctions as fsfun
import PropertyInputs as pinp
import UniversalInputs as uinp
import StructuralInputs as sinp
import Phase as phs
import Sensitivity as SA
import Periods as per

na = np.newaxis


def f_cropresidue_production():
    '''
    Stubble produced per kg of total grain (kgs of dry matter).

    This is a separate function because it is used in CropGrazing.py and Mach.py to calculate stubble penalties.
    '''
    stubble_prod_data = 1 / pinp.stubble['harvest_index'] - 1 * pinp.stubble['proportion_grain_harv']  # subtract 1*harv propn to account for the tonne of grain that was harvested and doesnt become stubble.
    stubble = pd.Series(data=stubble_prod_data, index=pinp.stubble['i_stub_landuse_idx'])
    return stubble



def crop_residue_all(params, r_vals, nv):
    '''
    Calculates the crop residue available, MD provided, volume required and the proportion of the way through
    the feed period that crop residue becomes available.

    Crop residue represents crop stubble and fodder crops (unharvested crops).
    Stubble and fodder are a key feed source for sheep during the summer months. In general sheep graze crop residues
    selectively, preferring the higher quality components.  Thus, they tend to eat grain first followed
    by leaf and finally stem. To allow optimisation of the quantity of the stubble grazed and to reflect selective
    grazing the total crop residues are divided into four categories (A, B, C & D). The higher categories are better
    quality but generally lower quantity. Consumption of a higher quality category allows the consumption of a lower
    category (e.g. sheep can not consume any of category B until some of category A has been consumed).

    For cereals, category A is mainly grain and leaf blade,
    category B is mainly leaf blade, leaf sheath and cocky chaff, category C is mainly cocky chaff and
    stem and category D is the remaining fraction that is not grazed. The total mass of crop residues at first
    grazing (harvest for stubble and an inputted date for fodder) is calculated as a product of the grain yield and harvest index.
    Overtime if the feed is not consumed it deteriorates in quality and quantity due to adverse effects of
    weather and the impact of sheep trampling.

    To represent crop residues in AFO requires the proportion of each category, the DMD of each category and the
    proportion of each component in each category. The DMD of each component (grain , leaf, sheath, stalk) has been
    determined by other work :cite:p:`RN108` and can be used to determine the proportion of each component in each category based
    on the DMD of each category. The quantity and DMD of each crop residue category were determined using the AFO
    sheep generator (documented in a future section). The DMD of the feed was altered until the liveweight change of
    the sheep in the simulation matched that of an equivalent sheep in a stubble trial (Riggall 2017 pers comm).
    This provided the feed DMD and the intake required to achieve the given liveweight. Based on the number of
    sheep and the total crop residue available in the trial the simulation results can be extrapolated to provide
    the crop residue DMD for different levels of intake. These results can be summaries into the 4 crop residue categories
    providing the DMD and proportion of the total crop residue in each.

    The energy provided from consuming each crop residue category is calculated from DMD. Like pasture, crop residue
    FOO is expressed in units of dry matter (excluding moisture) therefore feed energy is expressed as M/D
    (does not require dry matter content conversion). The volume of each crop residue category is calculated
    based on both the quality and availability of the feed.

    Farmer often rake and burn crop residue in preparation for the following seeding. This is represented as a
    cost see Phase.py for further information.

    Stubble grazing optimisation in AFO includes:

        - The time to start grazing of each stubble
        - The class of stock that grazes the stubble
        - The duration of grazing
        - The amount of supplementary required in addition to stubble (to meet alternative LW profiles)


    '''
    '''
    Stubble definitions:

    Total Grain = HI * (above ground) biomass
    Leaf + Stem = (1-HI) * biomass
    Harvested grain = (1 - spilt%) * Total grain
    Spilt grain = spilt% * Total grain
    Stubble = Leaf + Stem + Spilt grain
    
    Spilt grain as a proportion of the stubble = (HI * spilt %) / (1 - HI(1 - spilt%))
    '''

    ##nv stuff
    len_nv = nv['len_nv']
    nv_is_not_confinement_f = np.full(len_nv, True)
    nv_is_not_confinement_f[-1] = np.logical_not(nv['confinement_inc']) #if confinement is included the last nv pool is confinement.
    me_threshold_fp6z = np.swapaxes(nv['nv_cutoff_ave_p6fz'], axis1=0, axis2=1)
    stub_me_eff_gainlose = pinp.stubble['i_stub_me_eff_gainlose']

    ##create mask which is stubble available. Stubble is available from the period harvest starts to the beginning of the following growing season.
    ##if the end date of the fp is after harvest then stubble is available.
    fp_end_p6z = per.f_feed_periods()[1:].astype('datetime64[D]')
    fp_start_p6z = per.f_feed_periods()[:-1].astype('datetime64[D]')
    harv_date_zk = zfun.f_seasonal_inp(pinp.crop['start_harvest_crops'].values, numpy=True, axis=1).swapaxes(0,1).astype(np.datetime64)
    mask_stubble_exists_p6zk = fp_end_p6z[...,na] > harv_date_zk  #^this may need to become an input to handle chaff piles which may be grazed after the brk
    peirod_is_harvest_p6zk = np.logical_and(fp_end_p6z[...,na] >= harv_date_zk, fp_start_p6z[...,na] <= harv_date_zk)

    #############################
    # Total stubble production  #
    #############################
    ##calc yield - frost and seeding rate not accounted for because they don't effect stubble.
    rot_yields_rkl_p7z = phs.f_rot_yield(for_stub=True)
    ##calc stubble
    residue_per_grain_k = f_cropresidue_production()
    rot_stubble_rkl_p7z = rot_yields_rkl_p7z.mul(residue_per_grain_k, axis=0, level=1)

    #########################
    # deterioration         #
    #########################
    ##days since harvest (calculated from the end date of each fp)
    days_since_harv_p6zk = fp_end_p6z[...,na] - harv_date_zk.astype('datetime64[D]')
    days_since_harv_p6zk[days_since_harv_p6zk.astype(int)<0] = days_since_harv_p6zk[days_since_harv_p6zk.astype(int)<0] + 365  #add 365 to the periods at the start of the year because as far as stubble goes they are after harvest
    average_days_since_harv_p6zk = days_since_harv_p6zk - np.minimum(days_since_harv_p6zk, (fp_end_p6z - fp_start_p6z)[...,na])/2 #subtract half the length of current period to get the average days since harv. Minimum is to handle the period when harvest occurs.
    average_days_since_harv_p6zk = average_days_since_harv_p6zk.astype(float)

    ##calc the quantity decline % for each period - used in transfer constraints, need to average the number of days in the period of interest
    quant_declined_p6zk = (1 - pinp.stubble['quantity_deterioration']) ** average_days_since_harv_p6zk.astype(float)

    ##calc the quality decline % for each period
    ###quality is inputted for the paddock trial date. Therefore use days_since_trial to scale quality.
    average_days_since_trial_p6zk = average_days_since_harv_p6zk - pinp.stubble['i_calibration_offest'] #days will be negative between harvest and trial start
    qual_declined_p6zk = (1 - pinp.stubble['quality_deterioration']) ** average_days_since_trial_p6zk.astype(float)

    ###############
    # M/D & vol   #
    ###############
    '''
    This section creates a df that contains the M/D for each stubble category for each crop and 
    the equivalent for vol. This is used by live stock.
    
    1) read in stubble component composition, calculated by the sim (stored in an excel file)
    2) converts total dmd to dmd of category 
    3) calcs ri quantity and availability 
    4) calcs the md of each stubble category (dmd to MD)
    
    '''
    n_crops = len(pinp.stubble['i_stub_landuse_idx'])
    n_seasons = zfun.f_keys_z().shape[0]

    ##read in category info frpm xl
    cat_propn_s1k = pd.read_excel('stubble sim.xlsx',header=None, engine='openpyxl')
    cat_propn_ks1 = cat_propn_s1k.values.T

    ##quality of each category in each period
    ###scale dmd at the trial date to each period.
    stub_cat_qual_s1 = pinp.stubble['i_stub_cat_dmd_s1']
    dmd_cat_p6zks1 = stub_cat_qual_s1 * qual_declined_p6zk[...,na]

    ##calc relative quality before converting dmd to md - note that the equation system used is the one selected for dams in p1 - currently only cs function exists
    if uinp.sheep['i_eqn_used_g1_q1p7'][6,0]==0: #csiro function used
        ri_quality_p6zks1 = fsfun.f_rq_cs(dmd_cat_p6zks1, pinp.stubble['clover_propn_in_sward_stubble'])

    # ##ri availability (not calced anymore - stubble uses ra=1 now) - first calc stubble foo (stub available) this is the average from all rotations and lmus because we just need one value for foo (crop residue volume is assumed to be the same across lmu - the extra detail could be added)
    # ###try calc the base yield for each crop but if the crop is not one of the rotation phases then assign the average foo (this is only to stop error. it doesnt matter because the crop doesnt exist so the stubble is never used)
    # base_yields = rot_yields_rkl_p7z.droplevel(0, axis=0).groupby(axis=1, level=1).sum() #drop rotation index and sum p7 axis (just want total yield to calc pi)
    # base_yields = base_yields.replace(0,np.NaN) #replace 0 with nan so if yield inputs are missing (eg set to 0) the foo is still correct (nan gets skipped in pd.mean)
    # stub_foo_harv_zk = np.zeros((n_seasons, n_crops))
    # for crop, crop_idx in zip(pinp.stubble['i_stub_landuse_idx'], range(n_crops)):
    #     try:
    #         stub_foo_harv_zk[:, crop_idx] = base_yields.loc[crop].mean(axis=0) * residue_per_grain_k.loc[crop]
    #     except KeyError: #if the crop is not in any of the rotations assign average foo to stop error - this is not used so could assign any value.
    #         stub_foo_harv_zk[:,crop_idx] = base_yields.mean(axis=0) * residue_per_grain_k.mean()
    # stub_foo_harv_zk = np.nan_to_num(stub_foo_harv_zk) #replace nan with 0 (only wanted nan for the mean)
    ###adjust the foo for each category because the good stuff is eaten first therefore there is less foo when the sheep start eating the poorer stubble
    # cat_propn_rolled_ks1 = np.roll(cat_propn_ks1, shift=1, axis=1) #roll along the cat axis. So that the previous cat lines up with the current cat
    # cat_propn_rolled_ks1[:, 0] = 0 #set the first slice to 0 because no stubble is consumed before cat A is consumed eg there is 100% of foo available when sheep are consuming cat A
    # cat_cum_propn_ks1 = np.cumsum(cat_propn_rolled_ks1, axis=1) #cumulative sum of the component sizes.
    # stubble_foo_zks1 = stub_foo_harv_zk[..., na] *  (1 - cat_cum_propn_ks1)
    ###adjust for quantity delcine due to deterioration
    # stubble_foo_p6zks1 = stubble_foo_zks1 * quant_declined_p6zk[..., na]
    ###ri availability
    # hf = fsfun.f_hf(pinp.stubble['i_hr'])  # height factor
    # if uinp.sheep['i_eqn_used_g1_q1p7'][5,0]==0: #csiro function used - note that the equation system used is the one selected for dams in p1
    #     ri_availability_p6zks1 = fsfun.f_ra_cs(stubble_foo_p6zks1, hf)
    # elif uinp.sheep['i_eqn_used_g1_q1p7'][5,0]==1: #Murdoch function used - note that the equation system used is the one selected for dams in p1
    #     ri_availability_p6zks1 = fsfun.f_ra_mu(stubble_foo_p6zks1, hf)

    ##combine ri quality and ri availability to calc overall vol (potential intake) - use ra=1 for stubble (same as stubble sim)
    ri_p6zks1 = fsfun.f_rel_intake(1, ri_quality_p6zks1, pinp.stubble['clover_propn_in_sward_stubble'])
    vol_p6zks1 = (1000 / ri_p6zks1) / (1 + SA.sap['pi'])
    vol_p6zks1 = vol_p6zks1 * mask_stubble_exists_p6zk[..., na] #stop md being provided if stubble doesnt exist
    vol_fp6zks1 = vol_p6zks1 * nv_is_not_confinement_f[:,na,na,na,na] #me from stubble is 0 in the confinement pool

    ##convert dmd to M/D
    ## Stubble doesn't include calculation of effective mei because stubble is generally low quality feed with a wide variation in quality within the sward.
    ## Therefore, there is scope to alter average diet quality by altering the grazing time and the proportion of the stubble consumed.
    md_p6zks1 = np.clip(fsfun.dmd_to_md(dmd_cat_p6zks1), 0, np.inf)
    md_p6zks1 = md_p6zks1 * mask_stubble_exists_p6zk[...,na] #stop md being provided if stubble doesnt exist
    ##reduce me if nv is higher than livestock diet requirement.
    md_fp6zks1 = fsfun.f_effective_mei(1000, md_p6zks1, me_threshold_fp6z[...,na,na]
                                       , nv['confinement_inc'], ri_p6zks1, stub_me_eff_gainlose)

    md_fp6zks1 = md_fp6zks1 * nv_is_not_confinement_f[:,na,na,na,na] #me from stubble is 0 in the confinement pool

    ###########
    #trampling#
    ###########
    #for now this is just a single number however the input could be changed to per period, if this is changed some of the dict below would need to be dfs the stacked - so they account for period
    tramp_effect_ks1 = pinp.stubble['trampling'][:,na] * cat_propn_ks1

    ################################
    # allow access to next category#
    ################################

    ##quantity of cat A stubble provided from 1t of total stubble at harvest
    cat_a_prov_p6zks1 = 1000 * cat_propn_ks1 * np.logical_and(np.arange(len(pinp.stubble['i_stub_cat_idx']))==0
                                                      ,peirod_is_harvest_p6zk[...,na]) #Only cat A is provides at harvest

    ##amount of available stubble required to consume 1t of each cat in each fp
    stub_req_ks1 = 1000*(1+tramp_effect_ks1)

    ##amount of next category provide by consumption of current category.
    stub_prov_ks1 = np.roll(cat_propn_ks1, shift=-1,axis=-1)/cat_propn_ks1*1000
    stub_prov_ks1[:,-1] = 0 #final cat doesnt provide anything


    ##############################
    #transfers between periods   #
    ##############################
    ##transfer a given cat to the next period. Only cat A is available at harvest - it comes from the rotation phase.
    stub_transfer_prov_p6zk = 1000 * np.roll(quant_declined_p6zk, shift=-1, axis=0)/quant_declined_p6zk #divide to capture only the decay during the curent period (quant_decline is the decay since harv)
    stub_transfer_prov_p6zk = stub_transfer_prov_p6zk * mask_stubble_exists_p6zk  #no transfer can occur when stubble doesnt exist
    stub_transfer_prov_p6zk = stub_transfer_prov_p6zk * np.roll(np.logical_not(peirod_is_harvest_p6zk), -1, 0) #last yrs stubble doesnt transfer past the following harv.

    ##transfer requirment - mask out harvest period because last years stubble can not be consumed after this years harvest.
    stub_transfer_req_p6zk = 1000 * mask_stubble_exists_p6zk   # No transfer can occur when stubble doesnt exist or at harvest.

    ###############
    #harvest p con# stop sheep consuming more than possible because harvest is not at the start of the period
    ###############
    #how far through each period does harv start? note: 0 for each period harv doesn't start in. Used to calc stub consumption limit in harv period
    fp_len_p6z = fp_end_p6z - fp_start_p6z
    cons_propn_p6zk = np.clip(fun.f_divide(fp_len_p6z[...,na] - (fp_end_p6z[...,na] - harv_date_zk), fp_len_p6z[...,na]),0, np.inf)
    cons_propn_p6zk[cons_propn_p6zk>1] = 0

    ######################
    #apply season mask   #
    ######################
    ##mask
    mask_fp_z8var_p6z = zfun.f_season_transfer_mask(fp_start_p6z, z_pos=-1, mask=True)

    ##apply mask
    cons_propn_p6zk = cons_propn_p6zk * mask_fp_z8var_p6z[...,na]
    stub_transfer_prov_p6zk = stub_transfer_prov_p6zk * mask_fp_z8var_p6z[...,na]
    stub_transfer_req_p6zk = stub_transfer_req_p6zk * mask_fp_z8var_p6z[...,na]
    cat_a_prov_p6zks1 = cat_a_prov_p6zks1 * mask_fp_z8var_p6z[...,na,na]
    md_fp6zks1 = md_fp6zks1 * mask_fp_z8var_p6z[...,na,na]
    vol_fp6zks1 = vol_fp6zks1 * mask_fp_z8var_p6z[...,na,na]

    #########
    ##keys  #
    #########
    ##keys
    keys_k = np.array(pinp.stubble['i_stub_landuse_idx'])
    keys_p6 = pinp.period['i_fp_idx']
    keys_s1 = pinp.stubble['i_stub_cat_idx']
    keys_f  = np.array(['nv{0}' .format(i) for i in range(len_nv)])
    keys_z = zfun.f_keys_z()


    ##array indexes
    ###stub transfer (cat b & c)
    arrays_ks1 = [keys_k, keys_s1]
    ###category A req
    arrays_p6zks1 = [keys_p6, keys_z, keys_k, keys_s1]
    ###md & vol
    arrays_fp6zks1 = [keys_f, keys_p6, keys_z, keys_k, keys_s1]
    ###harv con & feed period transfer
    arrays_p6zk = [keys_p6, keys_z, keys_k]

    ################
    ##pyomo params #
    ################

    ##stubble produced per tonne of grain yield - this is df so don't need to build index.
    params['rot_stubble'] = rot_stubble_rkl_p7z.stack([0,1]).to_dict()

    ##'require' params ie consuming 1t of stubble B requires 1.002t from the constraint (0.002 accounts for trampling)
    params['transfer_req'] = fun.f1_make_pyomo_dict(stub_req_ks1, arrays_ks1)

    ###'provide' from cat to cat ie consuming 1t of cat A provides 2t of cat b
    params['transfer_prov'] = fun.f1_make_pyomo_dict(stub_prov_ks1, arrays_ks1)

    ###harv con
    params['cons_prop'] = fun.f1_make_pyomo_dict(cons_propn_p6zk, arrays_p6zk)

    ###feed period transfer
    params['stub_transfer_prov'] = fun.f1_make_pyomo_dict(stub_transfer_prov_p6zk, arrays_p6zk)
    params['stub_transfer_req'] = fun.f1_make_pyomo_dict(stub_transfer_req_p6zk, arrays_p6zk)

    ###category A transfer 'require' param
    params['cat_a_prov'] = fun.f1_make_pyomo_dict(cat_a_prov_p6zks1, arrays_p6zks1)

    ##md
    params['md'] = fun.f1_make_pyomo_dict(md_fp6zks1, arrays_fp6zks1)

    ##vol
    params['vol'] = fun.f1_make_pyomo_dict(vol_fp6zks1, arrays_fp6zks1)


