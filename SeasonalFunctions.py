'''
Seasonal functions used across modules
'''

##import python modules
import numpy as np
import pandas as pd
na=np.newaxis

##import AFO modules - should only import input modules
import PropertyInputs as pinp
import Functions as fun




def f_z_prob(keep_z=False):
    '''Calc the prob of each active season.

    :param keep_z: True means the active z axis is kept even in steady state model. This is used for the season input handling.
    '''
    steady_state_bool = pinp.general['steady_state'] or np.count_nonzero(pinp.general['i_mask_z']) == 1
    if steady_state_bool and not keep_z:
        z_prob = np.array([1])
    else:
        ##season mask - controls which seasons are included
        z_mask = pinp.general['i_mask_z']
        ##adjust season prob accounting for the seasons which are not included
        z_prob = np.array(pinp.general['i_season_propn_z'])
        z_prob = z_prob[z_mask]
        z_prob = z_prob / sum(z_prob)
    return z_prob


def f_seasonal_inp(inp, numpy=False, axis=0, level=0):
    '''
    This function handles the seasonal axis for inputs that are impacted by season type.
    If the discrete version of the model is being run the inputs which are seasonally effected can be generated by 2 methods
    returning an array with a singleton z axis:

        1. Take the weighted average of the inputs for different seasons
        2. Take the first slice of the z axis which is the user defined 'typical' season.

    If the stochastic version is being run this function masks out any un wanted
    seasons returning an input with an active season axis.

    .. note::
        For numpy z axis can be any but for pandas z must be column (if you want to change this the function will need mods).

    :param inp: the input being adjusted.
    :param numpy: boolean stating if the input is a numpy array.
    :param axis: the axis number where z is located.
    :param level: for pandas which level is season axis (if multi index).
    :return: Input array with a treated z axis.
    '''
    ##season mask - controls which seasons are included
    z_mask = pinp.general['i_mask_z']
    ##calc season prob accounting for the seasons which are not included
    z_prob = f_z_prob(keep_z=True)

    if numpy:
        ##mask the season types
        inp = np.compress(z_mask, inp, axis)

        ##weighted average if steady state
        if pinp.general['steady_state']:
            try:  # in case array is datearray
                inp = np.expand_dims(np.average(inp, axis=axis, weights=z_prob), axis)
            except TypeError:
                n_inp = inp.astype("datetime64[ns]").astype(np.int64)
                n_inp = np.expand_dims(np.average(n_inp, axis=axis, weights=z_prob), axis)
                inp = n_inp.astype("datetime64[ns]")
                # inp = n_inp.astype('M8[us]').astype('O') #converts to datetime

    else:
        ##mask the season types
        keys_z = pinp.general['i_z_idx'][z_mask]
        if inp.columns.nlevels > 2: #if statement required because can't convert one element to tuple
            slc_none = tuple([slice(None)] * (inp.columns.nlevels - 1)) #makes a slice(none) for each column level except season.
            inp = inp.loc[:, (keys_z, slc_none)]
        elif inp.columns.nlevels > 1:
            slc_none = slice(None)
            inp = inp.loc[:, (keys_z, slc_none)]
        else:
            inp = inp.loc[:,z_mask]

        ##weighted average if steady state
        if pinp.general['steady_state']:
            try: #in case df is datearray
                z_prob = pd.Series(z_prob, index=keys_z)
                if axis==0:
                    sum_level = list(range(inp.index.nlevels))
                else:
                    sum_level = list(range(inp.columns.nlevels))

                del sum_level[level]
                if sum_level == []:
                    inp = inp.mul(z_prob, axis=axis, level=level).sum(axis=axis)
                    inp = pd.concat([inp],keys=[keys_z[0]],axis=axis) #add z0 index key
                else:
                    inp = inp.mul(z_prob, axis=axis, level=level).sum(axis=axis, level=sum_level)
                    inp = pd.concat([inp],keys=[keys_z[0]],axis=axis) #add z0 index key
                    col_level_order = sum_level[:]
                    col_level_order.insert(level,0)
                    inp = inp.reorder_levels(col_level_order, axis=axis)
            except TypeError:
                #this won't work if columns have two levels (would need to reshape into multi d numpy do the average then reshape to 2-d)
                n_inp = inp.values.astype(np.int64)
                n_inp = np.average(n_inp, axis=axis, weights=z_prob)
                n_inp = n_inp.astype("datetime64[ns]")
                # n_inp = n_inp.astype('M8[us]').astype('O') #converts to datetime
                col = pd.MultiIndex.from_tuples([inp.columns[0]])
                inp = pd.DataFrame(n_inp, index=inp.index, columns=col)
    return inp

def f_keys_z():
    '''Returns the index/keys for the z axis'''
    if pinp.general['steady_state']:
        keys_z = np.array([pinp.general['i_z_idx'][pinp.general['i_mask_z']][0]]).astype('str')
    else:
        keys_z = pinp.general['i_z_idx'][pinp.general['i_mask_z']].astype('str')
    return keys_z


def f_parent_z(season_start_z8, date_initiate_z8, index_z8):
    '''
    Create an association pointing at each seasons parent season

    '''
    # create z9 versions of params (move z8 to the end) - this is required for situations when other axis exist
    index_z9 = np.moveaxis(index_z8, source=0, destination=-1)
    date_initiate_z9 = np.moveaxis(date_initiate_z8, source=0, destination=-1)

    # Identify the highest weather-year previous to this one that is initiated earlier.
    parent_z8 = np.max(index_z9 * (date_initiate_z9 < date_initiate_z8[...,na])
                      * (index_z9 < index_z8[...,na]),axis=-1)
    # if this weather-year is initiated at the break then it is it’s own parent (index_z)
    parent_z = fun.f_update(parent_z8, index_z8, date_initiate_z8 == season_start_z8)
    return parent_z


def f_season_transfer_mask(period_dates_pz, z_pos, period_is_seasonstart_pz=False, period_axis_pos=0, mask=False):
    '''
    Seasons are masked out until the point in the year when they are identified. At the point of identification
    the parent season provides the transfer parameters to the child season. This transferring method ensures the
    model has the same management across seasons until they are identified. For example, if there are two seasons, a
    good and a bad, that are identified in spring. Both seasons must have the same management through the beginning of
    the year until spring (because the farmer doesn't know if they are having the good or bad year until spring).

    :param period_dates_pz: period dates (eg dvp or cashflow) without end date of last period
    :param z_pos: z axis position
    :param period_is_seasonstart_pz: boolean array with true for season start period
    :param period_axis_pos: axis position of the period in the period date array. (argument not required when generating mask)
    :param mask: Boolean if True the function simply returns the z8var mask.
    :return: within season transfer (z8z9) masks for require and provide.
    '''
    ##inputs
    date_initiate_z = f_seasonal_inp(pinp.general['i_date_initiate_z'], numpy=True, axis=0).astype('datetime64[D]')
    bool_steady_state = pinp.general['steady_state'] or np.count_nonzero(pinp.general['i_mask_z']) == 1
    if bool_steady_state:
        len_z = 1
    else:
        len_z = np.count_nonzero(pinp.general['i_mask_z'])
    index_z = np.arange(len_z)
    date_node_zm = f_seasonal_inp(pinp.general['i_date_node_zm'],numpy=True,axis=0).astype('datetime64[D]')  # treat z axis

    ##expand inputs to line z axis to the correct position
    date_node_zm = fun.f_expand(date_node_zm, z_pos-1, right_pos=-1)
    index_z = fun.f_expand(index_z, z_pos)
    date_initiate_z = fun.f_expand(date_initiate_z, z_pos)

    ##parent z
    start_of_season_z = date_node_zm[...,0]
    parent_z = f_parent_z(start_of_season_z, date_initiate_z, index_z)
    parent_z9 = np.moveaxis(parent_z, source=0, destination=-1)
    identity_z8z9 = fun.f_expand(np.identity(parent_z.shape[0]),z_pos-1, right_pos=-1)

    ##get dtype consistent
    period_dates_pz = period_dates_pz.astype('datetime64[D]')

    ##adjust period start dates to the base yr (dates must be between break of current season and break of next season)
    end_of_season_z = start_of_season_z + np.timedelta64(364,'D') #use 364 because end date is the day before brk.
    add_yrs = np.ceil(np.maximum(0,(start_of_season_z - period_dates_pz).astype('timedelta64[D]').astype(int) / 365))
    sub_yrs = np.ceil(np.maximum(0,(period_dates_pz - end_of_season_z).astype('timedelta64[D]').astype(int) / 365))
    adj_period_dates_pz = period_dates_pz + add_yrs * np.timedelta64(365, 'D') - sub_yrs * np.timedelta64(365, 'D')

    ##z8 mask when season is identified
    mask_z8var_pz = np.logical_or(date_initiate_z <= adj_period_dates_pz, bool_steady_state) #if it is steadystate then the z8 mask is just true.
    if mask:
        return mask_z8var_pz

    ##req mask
    mask_childz_req_pz = mask_z8var_pz

    ##prov mask. Parent seasons provide to child season until the child season is identified.
    ### set up some general masks that are required to create the prov mask
    rolled_mask_z8var_pz = np.roll(mask_z8var_pz,shift=-1,axis=period_axis_pos)
    rolled_mask_z9var_pz9 = np.swapaxes(rolled_mask_z8var_pz[...,na], z_pos-1, -1)
    mask_z9var_pz9 = np.swapaxes(mask_z8var_pz[...,na], z_pos-1, -1)

    ###provides to itself (the identity array) if the weather-year exist during the period
    prov_self_pz8z9 = mask_z8var_pz[...,na] * identity_z8z9
    # prov_self_pz8z9 = np.logical_and(prov_self_pz8z9, rolled_mask_z8var_pz[...,na])
    ###parent seasons only provide to child in the period prior to the child being identified
    prov_child_pz8z9 = mask_z8var_pz[...,na] * (index_z[...,na] == parent_z9)
    prov_child_pz8z9 = prov_child_pz8z9 * np.logical_and(np.logical_not(mask_z9var_pz9), rolled_mask_z9var_pz9)
    ###combine self and child prov
    mask_param_provz8z9_pz8z9 = np.logical_or(prov_self_pz8z9, prov_child_pz8z9)
    ###all weather years in the final period of the year (nextperiod_is_seasonstart) can provide to the initiating weather-years of the following year
    ####The following year is the next weather-year in the sequence or the start year for static equilibrium and single year DSP
    nextperiod_is_seasonstart_pz = np.roll(period_is_seasonstart_pz,shift=-1,axis=period_axis_pos)
    mask_param_provz8z9_pz8z9 = fun.f_update(mask_param_provz8z9_pz8z9, rolled_mask_z9var_pz9, nextperiod_is_seasonstart_pz[...,na])

    ##adjust z8z9 mask for between (only has true for the period that passes to season start) and within (only has true if period is not season start)
    mask_childz_reqwithin_pz = mask_childz_req_pz * np.logical_not(period_is_seasonstart_pz)
    mask_childz_reqbetween_pz = mask_childz_req_pz * period_is_seasonstart_pz
    mask_provwithinz8z9_pz8z9 = mask_param_provz8z9_pz8z9 * np.logical_not(nextperiod_is_seasonstart_pz[...,na])
    mask_provbetweenz8z9_pz8z9 = mask_param_provz8z9_pz8z9 * nextperiod_is_seasonstart_pz[...,na]

    return mask_provwithinz8z9_pz8z9, mask_provbetweenz8z9_pz8z9, mask_childz_reqwithin_pz, mask_childz_reqbetween_pz



def f1_z_period_alloc(item_start=0, item_length=np.timedelta64(1, 'D'), z_pos=-1):
    '''
    Allocation of item into season periods (p7).

    Cant be allocated across the season start (length is automatically adjusted in f_range_allocation to stop allocation
    going from the end of the periods to the start of the periods. This is because gets complicated if it crosses junction)
    e.g. post harvest jobs must be completed before the next season start.
    An item can be allocated in to multiple season periods as long as the dv exists in the same multiple season periods
    e.g. v_phase exists in all children therefore labour requirement can cross nodes.

    Note: Inputs required before season start (e.g. lime) are never applied on the basis of an expected landuse it will
    only be applied based on actual landuse. Because (i) although in the mind of a farmer these inputs are preseeding
    the model sees them as inputs at the end of the year (ii) the inputs are directly hooked to the phase selected.
    If this is a problem the solution is to make the preseeding inputs a desicion variable that allows landuses (you
    could select another landuse but the cost would be wasted). And season start would need to be prior to decision.

    Note: cashflow goes through a slightly different function that also calculates interest (it then calls this function).

    - Arrays must be numpy and broadcastable.
    - p7 axis must be in pos 0
    - item start must contain all axes (including z and p7)

    :param item_start: datetime64 item dates which are allocated into rotation periods. MUST contain all axis of the final array (singleton is fine)
    :param item_length: datetime64
    :param z_pos:
    :return:
    '''

    import Periods as per #import here since periods.py imports this module.

    date_season_node_p7z = per.f_season_periods()
    len_p7 = date_season_node_p7z.shape[0] - 1  # minus one because end date is not a period

    ##align axes
    p7_pos = -item_start.ndim
    date_node_p7etc = fun.f_expand(date_season_node_p7z, left_pos=z_pos, right_pos2=z_pos, left_pos2=p7_pos)
    shape = (len_p7,) + tuple(np.maximum.reduce([date_node_p7etc.shape[1:], item_start.shape[1:]]))  # create shape which has the max size, this is used for o array
    alloc_metc = fun.range_allocation_np(date_node_p7etc, item_start, item_length, opposite=True, shape=shape)

    ##mask z8
    mask_season_z8 = f_season_transfer_mask(date_node_p7etc[:-1,...],z_pos,mask=True) #slice off end date p7

    return alloc_metc * mask_season_z8


