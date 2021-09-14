
"""
author: young
#todo need to update this.
To capture debit and credit interest the year is split into bi-monthly cashflow periods. Activities with a
cost or income add to or remove from the cashflow balance. To support the sporadic nature of farming income
finance is often drawn from the bank throughout the year to fund costly operations such as seeding. This
is also represented in AFO however a user input exist which sets the maximum overdraw limit. At the end
of a period the positive or negative bank balance plus interest is transferred to the next period.

There is no representation of a starting cash balance. If it is included the model just selects the
highest amount because that earns the most interest. The model can get loan from bank if it needs
cash, so this does not affect model solution.

Tax is also not represented for several reasons:

#. There are several mechanisms by which farmers seek to lessen their tax liabilities. Not all
   are 'economically rational' and not all are easily represented in an LP model.

#. Many farmers nowadays invest in farm management deposits and income-averaging as a means
   of taxable income averaging and smoothing working capital borrowings. if the FMDs could be used
   'perfectly' then each year would have the same taxable profit. Thus, the optimal farm management
   is unaffected by the inclusion of tax.

#. AFO is a bioeconomic model with the aim of optimising farm management. It is not a finance model.

Asset value
    Asset value is the value of all assets on the first day of the cashflow year. It captures the opportunity
    cost of investing in farm assets including livestock, machinery and infrastructure (sheds, yards etc).
    The role of the asset value is to ensure that all assets that are selected have a return more than the
    interest cost, this ensures the optimal solution does not include assets that returns
    less than investing the same money in high interest savings (or to reduce core debt).
    This structure makes the static equilibrium model generate a result similar to a multi-period optimisation
    that accounts for interest cost of money.
    For livestock this ensures that the flock structure optimisation accounts for the opportunity cost
    of interest foregone from holding an animal for an extra year.

.. note:: To ensure accurate representation of asset opportunity cost the date when the assets are valued
    must be the date when the cashflow periods begin.

The cashflow operates in conjunction with the asset value in representing the opportunity cost of holding assets.
Livestock flock structure is the main 'decision' that is altered by the inclusion of an asset value. Without
interest if animals are sold early in the year there would not be an offsetting value that would
make early sale a ‘reasonable’ option. For example, selling the day after the asset is valued for the price
that the animal was valued should be an ‘equal’ outcome solution, but this only occurs if there is
interest ‘earned’ in the cashflow.

The interest rate for credit & debit are different for farmers ‘real money’ in the bank.
However, in the model very similar debit and credit interest rates are used (this can be changed by the user).
The reason equal interest rates are set as the default are:

#. Many farmers often have a core debt, so the farm cash position is usually negative even though
   their short term operating account may occasionally be positive. The differential interest
   rates are only justified if the farmer does not operate with a sweep facility to pay down
   core debt and then redraw when required later.
#. As discussed above the asset value and the cashflow operate together in the optimisation of
   flock structure. This implies that the interest rate for the cash flow should be the same as
   the discount rate for the asset value.


Minimum return on expenditure
    AFO tallies the total farm expenditure, adjusts it by a user defined return on expense factor and
    includes it in the objective to ensure the model achieves a minimum return on expenditure. The
    purpose of this is to represent farmer behaviour. It can also be used in the static equilibrium
    version to 'fudge' the risk associated with seasonal variation and reduce the optimal stocking rate
    to better align with on-farm values.
    The rate of MinROE is specified by the user and can be turned off. Comparison of the model output
    with on-farm benchmarking has been used to calibrate the selected value.

"""
##python modules
import pandas as pd
import numpy as np

##AFO modules
import UniversalInputs as uinp
import StructuralInputs as sinp
import PropertyInputs as pinp
import Periods as per
import Functions as fun

'''
interest
'''


def f_cashflow_allocation(amount,start,p_dates_c0p7,peakdebt_date,enterprise=None,length=1):
    '''
    This function calculate the interest earned on cashflow item, tallies up the total cashflow including interest
    and tallies up the working capital from a cashflow item.

    This function is complicated by the fact that some cashflow items occur over a date range. This is treated such that
    an proportion of the cashflow is received each day.

    All inputs must be broadcastable.

    :param amount: cost or income amount (pass in 1 to get just the allocation).
    :param start: datetime64 date when cashflow starts
    :param enterprise: enterprise
    :param peak_debt_date_c0: datetime64 date peak debt occurs
    :param p_dates_c0p7: datetime64 cashflow dates with c0 and p7 in position 0 and 1 respectively. Other axis can be included after p7.
    :param rate: yearly interest rate.
    :param length: int - time over which the cashflow is incurred
    '''

    # pandas = isinstance(amount,pd.DataFrame) or isinstance(amount,pd.Series)

    ##inputs
    rate = uinp.finance['i_interest']
    keys_c0 = np.expand_dims(sinp.general['i_enterprises_c0'], tuple(range(1, p_dates_c0p7.ndim)))
    # p_dates_c0p7z = per.f_cashflow_periods(pandas)
    # date_peakdebt_stock = pinp.sheep['i_date_peakdebt_stock_i'][pinp.sheep['i_mask_i']]
    # date_peakdebt_stock = date_peakdebt_stock.astype('datetime64').view('i8').mean(keepdims=True).astype('datetime64[us]') #take mean incase multiple tol included
    # date_peakdebt_crop = np.array([pinp.crop['i_date_peakdebt_crop']]).astype('datetime64[us]')
    # peakdebt_date_c0 = np.concatenate([date_peakdebt_stock,date_peakdebt_crop])
    peakdebt_date = np.broadcast_to(peakdebt_date, p_dates_c0p7.shape) #broadcast so that it can be indexed on p7

    ##build final arrays
    amount = np.expand_dims(amount, tuple(range(-p_dates_c0p7.ndim,-amount.ndim)))
    amount_shape = amount.shape
    start = np.expand_dims(start, tuple(range(-p_dates_c0p7.ndim,-start.ndim)))
    start_shape = start.shape
    p_dates_c0p7_shape = list(p_dates_c0p7.shape) #has to be a list because cant change tuple.
    p_dates_c0p7_shape[1] = p_dates_c0p7_shape[1] -1 #remove the last cashflow peirod because it is not a real period. It is just the end date.
    shape = np.maximum.reduce([amount_shape, start_shape, p_dates_c0p7_shape]) #create shape which has the max size, this is used for o array
    final_cashflow = np.zeros(shape)
    final_wc = np.zeros(shape)
    # amount = np.broadcast_to(amount, shape)
    # start = np.broadcast_to(start, shape)
    # length = np.broadcast_to(length, shape)
    # p_dates_c0p7 = np.broadcast_to(p_dates_c0p7, shape)

    ##adjust yr of cashflow occurence - this removes the singleton p7 axis from start
    add_yrs = np.ceil(np.maximum(0,(p_dates_c0p7[:,0,...] - start[:,0,...]).astype('timedelta64[D]').astype(int) / 365))
    sub_yrs = np.ceil(np.maximum(0,(start[:,0,...] - p_dates_c0p7[:,-1,...]).astype('timedelta64[D]').astype(int) / 365))
    start = start[:,0,...] + add_yrs * np.timedelta64(365, 'D') - sub_yrs * np.timedelta64(365, 'D')
    ###little check to ensure that all cashflow is all starting at least 1 day before the end cashflow date
    start = start - np.maximum(0, (start - (p_dates_c0p7[:,-1,...] - np.timedelta64(1, 'D'))).astype('timedelta64[D]').astype(int))

    ##handle cases where cost date + length is after the end of cashflow. in this situation length gets reduced
    length = np.minimum(length, (p_dates_c0p7[:,-1,...] - start).astype('timedelta64[D]').astype(int))

    total_principal_end = 0
    daily_payment = amount[:,0,...] / length #[:,0,...] to remove the singlton p7 axis

    ##start and end dates for the cashflow periods
    for p in range(p_dates_c0p7.shape[1]-1):
        ##cashflow period dates
        date_start_c0 = p_dates_c0p7[:,p,...]
        date_end_c0 = p_dates_c0p7[:,p + 1,...]
        peakdebt_date_c0 = peakdebt_date[:,p,...]

        ##princiapal at the begining of the p7 period (amount of cash at the begining of the period, inc interest from previous periods)
        principal_start = total_principal_end

        #
        # cashflow - principal and interest
        #
        ##calculate interest druing incur period (incur period is the time between the cashflow start and end)
        ###end date of incur period
        incur_end = start + length.astype('timedelta64[D]')
        ###length of incur period (days)
        incur_days = (np.minimum(date_end_c0, incur_end) - np.maximum(date_start_c0, start)).astype('timedelta64[D]').astype(int)
        incur_days = np.maximum(0, incur_days)
        ###interest on starting balance during the incur period - using formula: A = P (1 + r/n)**(t)
        principal_interest = principal_start * ((1 + rate / 365) ** incur_days - 1)
        ###daily payments plus interest on daily payments during the incur period - Using formula: Payment × ( ( ( (1 + r/n)^(t) ) - 1 ) / (r/n) )
        incur_amount = daily_payment * (((1 + rate / 365) ** incur_days - 1) / (rate / 365))

        ##calc interest over the period after payment incur has finished
        ###days from the end of incur to the end of the period
        post_incur_days = (date_end_c0 - np.maximum(date_start_c0, incur_end)).astype('timedelta64[D]').astype(int)
        post_incur_days = np.maximum(0, post_incur_days)
        ###balance at start of non incur period
        post_incur_start_balance = principal_start + principal_interest + incur_amount
        ###interest on balance after the incur period - using formula: A = P (1 + r/n)**(t)
        post_incur_interest = post_incur_start_balance * ((1 + rate / 365) ** post_incur_days - 1)

        ##cash at the end of the period
        cashflow_n_interest = principal_interest + incur_amount + post_incur_interest
        total_principal_end = post_incur_start_balance + post_incur_interest

        #
        # working capital constraint except that income or expense incurred after the peak debt date is excluded
        #
        ##calculate interest druing incur period (incur period is the time between the cashflow start and end)
        ###end date of incur period
        incur_end = start + length.astype('timedelta64[D]')
        ###length of incur period (days)
        incur_days = (np.minimum(date_end_c0, np.minimum(incur_end,peakdebt_date_c0)) - np.maximum(date_start_c0, start)).astype('timedelta64[D]').astype(int)
        incur_days = np.maximum(0, incur_days)
        ###interest on starting balance during the incur period - using formula: A = P (1 + r/n)**(t)
        wc_principal_interest = principal_start * ((1 + rate / 365) ** incur_days - 1)
        ###daily payments plus interest on daily payments during the incur period - Using formula: Payment × ( ( ( (1 + r/n)^(t) ) - 1 ) / (r/n) )
        wc_daily_interest = daily_payment * (((1 + rate / 365) ** incur_days - 1) / (rate / 365))

        ##calc interest over the period after payment incur has finished
        ###days from the end of incur to the end of the period
        post_incur_days = (np.maximum(date_start_c0,incur_end) - np.minimum(date_end_c0, peakdebt_date_c0)).astype('timedelta64[D]').astype(int)
        post_incur_days = np.maximum(0, post_incur_days)
        ###balance at start of non incur period
        wc_post_incur_start_balance = principal_start + wc_principal_interest + wc_daily_interest
        ###interest on balance after the incur period - using formula: A = P (1 + r/n)**(t)
        wc_post_incur_interest = wc_post_incur_start_balance * ((1 + rate / 365) ** post_incur_days - 1)

        ##cash at the end of the period
        wc = wc_principal_interest + wc_daily_interest + wc_post_incur_interest

        ##assign to final array
        final_cashflow[:,p,...] = cashflow_n_interest
        final_wc[:,p,...] = wc

    ##adjust for enterprise
    if enterprise is not None:
        final_cashflow = final_cashflow * (keys_c0==enterprise)

    return final_cashflow, final_wc


#################
#overheads      #
#################
def overheads(params, r_vals):
    '''
    Calculate overhead costs in each cashflow period and the associated interest.

    Overheads are ongoing business expenses that are not directly attributed to creating a product
    or service. In AFO the user has the discretion to add, remove or alter the overheads that are
    including. Examples of overhead costs include; electricity, gas, shire rates, licenses,
    professional services, insurance and household expense.
    '''
    length = 365 #overheads are incurred equally each day
    start_cashflow_stock = np.average(pinp.sheep['i_date_cashflow_stock_i'][i_mask_i])
    start_cashflow_crop = np.array([pinp.crop['i_date_cashflow_crop']])

    overheads = pinp.general['i_overheads']
    overheads = overheads.sum()
    overheads_stock = overheads/2
    overheads_crop = overheads/2

    f_cashflow_allocation(overheads_stock,start_cashflow_stock,'stk', length)
    f_cashflow_allocation(overheads_crop,start_cashflow_crop,'crp', length)
#need to add c0
    overheads = dict.fromkeys(sinp.general['cashflow_periods'], overheads)
    params['overheads'] = overheads
    r_vals['overheads'] = pd.Series(overheads)

#################
#Min ROE        #
#################
def f_min_roe():
    ##the default inputs for min roe are different for steady-state and stochastic version.
    ##but one SAV controls both inputs. So steady-state and stochastic can fairly be compared.
    if pinp.general['steady_state'] or np.count_nonzero(pinp.general['i_mask_z'])==1:
        min_roe = uinp.finance['minroe']
    else:
        min_roe = uinp.finance['minroe_dsp']
    return min_roe



#################
# report vals   #
#################

def finance_rep(r_vals):
    keys_c = sinp.general['cashflow_periods']
    r_vals['keys_c'] = keys_c
    r_vals['opportunity_cost_capital'] = uinp.finance['opportunity_cost_capital']
    r_vals['interest_rate'] = debit_interest()



