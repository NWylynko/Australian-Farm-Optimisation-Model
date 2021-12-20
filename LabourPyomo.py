# -*- coding: utf-8 -*-
"""
author: young

.. note:: Labour is uncondensed in pyomo. We have code which builds constraints for casual, perm and manager
    (rather than using a worker level set). The transfer labour variables do have a worker set which
    indicates what level of job is being done. The level is fixed for each constraint. Eg manager can do
    casual jobs, in con_sheep_anyone (sheep jobs that can be done by anyone) w (worker set) is fixed to ‘casual’.
    Eventually all the labour constraints could be condensed so there is one constraint for all the worker levels.
    This would require using the worker set as a set that is passed into the constraint. Would also need a
    param which indicates which level of working each source supplies eg casual needs to provide 0 manager
    level jobs.


"""

#python modules
from pyomo.environ import *

#AFO modules
import Labour as lab
import PropertyInputs as pinp
import StructuralInputs as sinp

def lab_precalcs(params, r_vals):
    '''
    Call crop precalc functions.

    :param params: dictionary which stores all arrays used to populate pyomo parameters.
    :param report: dictionary which stores all report values.

    '''
    lab.f_labour_general(params, r_vals)
    lab.f_perm_cost(params, r_vals)
    params['min_perm'] = pinp.labour['min_perm']
    params['max_perm'] = pinp.labour['max_perm']
    params['min_managers'] = pinp.labour['min_managers'] 
    params['max_managers'] = pinp.labour['max_managers']
                    


def f1_labpyomo_local(params, model):
    ''' Builds pyomo variables, parameters and constraints'''
    ############
    # variable #
    ############

    # Casual supervision
    model.v_casualsupervision_perm = Var(model.s_sequence_year, model.s_sequence, model.s_labperiods, model.s_season_types, bounds=(0,None),
                                         doc='hours of perm labour used for supervision of casual')
    model.v_casualsupervision_manager = Var(model.s_sequence_year, model.s_sequence, model.s_labperiods, model.s_season_types, bounds=(0,None),
                                            doc='hours of manager labour used for supervision of casual')

    # Amount of casual. Casual labour can be optimised for each period
    model.v_quantity_casual = Var(model.s_sequence_year, model.s_sequence, model.s_labperiods, model.s_season_types, bounds=(0,None),
                                  doc='number of casual labour used in each labour period')

    # Amount of permanent labour.
    max_perm = pinp.labour['max_perm'] if pinp.labour['max_perm'] != 'inf' else None  # if none convert to python None
    model.v_quantity_perm = Var(bounds=(pinp.labour['min_perm'],max_perm),
                                doc='number of permanent labour used in each labour period')

    # Amount of manager labour
    max_managers = pinp.labour['max_managers'] if pinp.labour[
                                                      'max_managers'] != 'inf' else None  # if none convert to python None
    model.v_quantity_manager = Var(bounds=(pinp.labour['min_managers'],max_managers),
                                   doc='number of manager/owner labour used in each labour period')

    # manager pool
    # labour for sheep activities (this variable transfers labour from source to sink)
    model.v_sheep_labour_manager = Var(model.s_sequence_year, model.s_sequence, model.s_labperiods, model.s_worker_levels, model.s_season_types, bounds=(0,None),
                                       doc='manager labour used by sheep activities in each labour period for each different worker level')

    # labour for rotation phase activities (this variable transfers labour from source to sink)
    model.v_phase_labour_manager = Var(model.s_sequence_year, model.s_sequence, model.s_labperiods, model.s_worker_levels, model.s_season_types, bounds=(0,None),
                                      doc='manager labour used by crop activities in each labour period for each different worker level')

    # labour for fixed activities (this variable transfers labour from source to sink)
    model.v_fixed_labour_manager = Var(model.s_sequence_year, model.s_sequence, model.s_labperiods, model.s_worker_levels, model.s_season_types, bounds=(0,None),
                                       doc='manager labour used by fixed activities in each labour period for each different worker level')

    # permanent pool
    # labour for sheep activities (this variable transfers labour from source to sink)
    model.v_sheep_labour_permanent = Var(model.s_sequence_year, model.s_sequence, model.s_labperiods, model.s_worker_levels, model.s_season_types, bounds=(0,None),
                                         doc='permanent labour used by sheep activities in each labour period for each different worker level')

    # labour for rotation phase activities (this variable transfers labour from source to sink)
    model.v_phase_labour_permanent = Var(model.s_sequence_year, model.s_sequence, model.s_labperiods, model.s_worker_levels, model.s_season_types, bounds=(0,None),
                                        doc='permanent labour used by crop activities in each labour period for each different worker level')

    # labour for fixed activities (this variable transfers labour from source to sink)
    model.v_fixed_labour_permanent = Var(model.s_sequence_year, model.s_sequence, model.s_labperiods, model.s_worker_levels, model.s_season_types, bounds=(0,None),
                                         doc='permanent labour used by fixed activities in each labour period for each different worker level')

    # casual pool
    # labour for sheep activities (this variable transfers labour from source to sink)
    model.v_sheep_labour_casual = Var(model.s_sequence_year, model.s_sequence, model.s_labperiods, model.s_worker_levels, model.s_season_types, bounds=(0,None),
                                      doc='casual labour used by sheep activities in each labour period for each different worker level')

    # labour for rotation phase activities (this variable transfers labour from source to sink)
    model.v_phase_labour_casual = Var(model.s_sequence_year, model.s_sequence, model.s_labperiods, model.s_worker_levels, model.s_season_types, bounds=(0,None),
                                     doc='casual labour used by crop activities in each labour period for each different worker level')

    # labour for fixed activities (this variable transfers labour from source to sink)
    model.v_fixed_labour_casual = Var(model.s_sequence_year, model.s_sequence, model.s_labperiods, model.s_worker_levels, model.s_season_types, bounds=(0,None),
                                      doc='casual labour used by fixed activities in each labour period for each different worker level')


    #########
    #param  #
    #########
    model.p_perm_hours = Param(model.s_labperiods, model.s_season_types, initialize= params['permanent hours'], default = 0.0, mutable=True, doc='hours worked by a permanent staff in each period')
    
    model.p_perm_supervision = Param(model.s_labperiods, model.s_season_types, initialize= params['permanent supervision'], default = 0.0, mutable=True, doc='hours of supervision required by a permanent staff in each period')
    
    model.p_perm_cost = Param(model.s_season_periods, model.s_season_types, initialize = params['perm_cost'], default = 0.0, doc = 'cost of a permanent staff for 1 yr')
    
    model.p_perm_wc = Param(model.s_enterprises, model.s_season_periods, model.s_season_types, initialize = params['perm_wc'], default = 0.0, doc = 'wc of a permanent staff for 1 yr')
    
    model.p_casual_cost = Param(model.s_season_periods, model.s_season_types, model.s_labperiods, initialize = params['casual_cost'], default = 0.0, doc = 'cost of a casual staff for each labour period')
    
    model.p_casual_wc = Param(model.s_enterprises, model.s_season_periods, model.s_season_types, model.s_labperiods, initialize = params['casual_wc'], default = 0.0, doc = 'wc of a casual staff for each labour period')
    
    model.p_casual_hours = Param(model.s_labperiods, model.s_season_types, initialize= params['casual hours'], default = 0.0, doc='hours worked by a casual staff in each period')
    
    model.p_casual_supervision = Param(model.s_labperiods, model.s_season_types, initialize= params['casual supervision'], default = 0.0, doc='hours of supervision required by a casual staff in each period')
    
    model.p_manager_hours = Param(model.s_labperiods, model.s_season_types, initialize= params['manager hours'], default = 0.0, doc='hours worked by a manager in each period')
    
    model.p_manager_cost = Param(model.s_season_periods, model.s_season_types, initialize = params['manager_cost'], default = 0.0, doc = 'cost of a manager for 1 yr')
    
    model.p_manager_wc = Param(model.s_enterprises, model.s_season_periods, model.s_season_types, initialize = params['manager_wc'], default = 0.0, doc = 'wc of a manager for 1 yr')
    
    model.p_casual_upper = Param(model.s_labperiods, model.s_season_types, initialize = params['casual ub'], default = 0.0,  doc = 'casual availability upper bound')
    
    model.p_casual_lower = Param(model.s_labperiods, model.s_season_types, initialize = params['casual lb'], default = 0.0, doc = 'casual availability lower bound')

    ###############################
    #call local constraints       #
    ###############################
    f_con_casual_bounds(model)
    f_con_casual_supervision(model)
    f_con_labour_transfer_manager(model)
    f_con_labour_transfer_permanent(model)
    f_con_labour_transfer_casual(model)


###############################
#local constraints            #
###############################
def f_con_casual_bounds(model):
    '''
    Optional constraint to bound the level of casual staff in each period.
    '''
    #this can't be done with variable bounds because it's not a constant value for each period (seeding and harv may differ)
    def casual_labour_availability(model,q,s,p,z):
        return  (model.p_casual_lower[p,z], model.v_quantity_casual[q,s,p,z], model.p_casual_upper[p,z]) #pyomos way of: lower <= x <= upper
    model.con_casual_bounds = Constraint(model.s_sequence_year, model.s_sequence, model.s_labperiods, model.s_season_types, rule = casual_labour_availability, doc='bounds the casual labour in each period')

def f_con_casual_supervision(model):
    '''
    Casual labourers require a certain amount of supervision per period. Supervision can be provided
    by either permanent or manager staff. This constraint ensures ensures that the supervision requirement
    is met.
    '''
    ##casual supervision - can be done by either perm or manager
    def transfer_casual_supervision(model,q,s,p,z):
        return -model.v_casualsupervision_manager[q,s,p,z] - model.v_casualsupervision_perm[q,s,p,z] + (model.p_casual_supervision[p,z] * model.v_quantity_casual[q,s,p,z]) <= 0
    model.con_casual_supervision = Constraint(model.s_sequence_year, model.s_sequence, model.s_labperiods, model.s_season_types, rule = transfer_casual_supervision, doc='casual require supervision from perm or manager')

def f_con_labour_transfer_manager(model):
    '''Transfer manager labour to livestock, cropping, fixed and supervising activities.'''
    #manager, this is a little more complex because also need to subtract the supervision hours off of the manager supply of workable hours
    def labour_transfer_manager(model,q,s,p,z):
        return -(model.v_quantity_manager * model.p_manager_hours[p,z]) + (model.v_quantity_perm * model.p_perm_supervision[p,z]) + model.v_casualsupervision_manager[q,s,p,z]      \
        + sum(model.v_sheep_labour_manager[q,s,p,w,z] + model.v_phase_labour_manager[q,s,p,w,z] + model.v_fixed_labour_manager[q,s,p,w,z] for w in model.s_worker_levels)  <= 0
    model.con_labour_transfer_manager = Constraint(model.s_sequence_year, model.s_sequence, model.s_labperiods, model.s_season_types, rule = labour_transfer_manager, doc='labour from manager to sheep and crop and fixed')

def f_con_labour_transfer_permanent(model):
    '''Transfer permanent labour to livestock, cropping, fixed and supervising activities.'''
    #permanent
    def labour_transfer_permanent(model,q,s,p,z):
        return -(model.v_quantity_perm * model.p_perm_hours[p,z]) + model.v_casualsupervision_perm[q,s,p,z]  \
        + sum(model.v_sheep_labour_permanent[q,s,p,w,z] + model.v_phase_labour_permanent[q,s,p,w,z] + model.v_fixed_labour_permanent[q,s,p,w,z] for w in model.s_worker_levels if w in sinp.general['worker_levels'][0:-1]) <= 0 #if statement just to remove unnecessary activities from lp output
    model.con_labour_transfer_permanent = Constraint(model.s_sequence_year, model.s_sequence, model.s_labperiods, model.s_season_types, rule = labour_transfer_permanent, doc='labour from permanent staff to sheep and crop and fixed')

def f_con_labour_transfer_casual(model):
    '''Transfer casual labour to livestock, cropping and fixed activities.'''
    #casual note perm and manager can do casual tasks - variables may need to change name so to be less confusing
    def labour_transfer_casual(model,q,s,p,z):
        return -(model.v_quantity_casual[q,s,p,z] *  model.p_casual_hours[p,z])  \
            + sum(model.v_sheep_labour_casual[q,s,p,w,z] + model.v_phase_labour_casual[q,s,p,w,z] + model.v_fixed_labour_casual[q,s,p,w,z] for w in model.s_worker_levels if w in sinp.general['worker_levels'][0])  <= 0  #if statement just to remove unnecessary activities from lp output
    model.con_labour_transfer_casual = Constraint(model.s_sequence_year, model.s_sequence, model.s_labperiods, model.s_season_types, rule = labour_transfer_casual, doc='labour from casual staff to sheep and crop and fixed')



#######################
#labour cost function #
#######################

#sum the cost of perm, casual and manager labour.

def f_labour_cost(model,q,s,p7,z):
    '''
    Calculate the total cost of the selected labour activities. Perm and manager labour cost is allocated to each
    enterprise based on the fixed cost allocation proportion.

    Used in global constraint (con_cashflow). See CorePyomo
    '''
    cas = sum(model.v_quantity_casual[q,s,p5,z] * model.p_casual_cost[p7,z,p5] for p5 in model.s_labperiods)
    perm = model.v_quantity_perm * model.p_perm_cost[p7,z]
    manager = model.v_quantity_manager * model.p_manager_cost[p7,z]
    return cas + perm + manager

def f_labour_wc(model,q,s,c0,p7,z):
    '''
    Calculate the total wc of the selected labour activities. Perm and manager labour wc is allocated to each
    enterprise based on the fixed wc allocation proportion.

    Used in global constraint (con_workingcap). See CorePyomo
    '''
    cas = sum(model.v_quantity_casual[q,s,p5,z] * model.p_casual_wc[c0,p7,z,p5] for p5 in model.s_labperiods)
    perm = model.v_quantity_perm * model.p_perm_wc[c0,p7,z]
    manager = model.v_quantity_manager * model.p_manager_wc[c0,p7,z]
    return cas + perm + manager





