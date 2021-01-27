"""
==================
Demographic Models
==================

This module contains tools for modeling the core demography in
multi-state lifetable simulations.

"""
import numpy as np
from scipy import optimize
import pdb


class BasePopulation:
    """
    This component implements the core population demographics: age, sex,
    population size.

    The configuration options for this component are:

    ``population_size``
        The number of population cohorts (**must be specified**).
    ``max_age``
        The age at which cohorts are removed from the population
        (default: 110).

    .. code-block:: yaml

       configuration
           population:
               population_size: 44 # Male and female 5-year cohorts, 0 to 109.
               max_age: 110        # The age at which cohorts are removed.

    """

    configuration_defaults = {
        'population': {
            'max_age': 110,
        }
    }

    def load_population_data(self, builder):
        pop_agg = builder.data.load('population.agg')
        pop_agg = pop_agg[['age', 'sex', 'value']].rename(columns={'value': 'population'})
        
        pop_prop = builder.data.load('population.prop')
        pop_prop = pop_prop[['age', 'sex', 'strata', 'value']].rename(columns={'value': 'prop'})
        
        pop_data = pop_agg.merge(pop_prop, how='inner', on=['age', 'sex'])
        # TODO. Divide by the sum of prop for matching age and sex in case prop does not add to 1.
        pop_data['population'] *= pop_data['prop']
        pop_data.drop(columns=['prop'], axis=1, inplace=True)
        pop_data['bau_population'] = pop_data['population']
        
        return pop_data


    @property
    def name(self):
        return 'base_population'
    
    def setup(self, builder):
        """Load the population data."""
        columns = ['age', 'sex', 'strata', 'population', 'bau_population',
                   'acmr', 'acmr_prop', 'bau_acmr',
                   'pr_death', 'bau_pr_death', 'deaths', 'bau_deaths',
                   'yld_rate', 'yld_prop', 'bau_yld_rate',
                   'person_years', 'bau_person_years',
                   'HALY', 'bau_HALY']

        self.pop_data = self.load_population_data(builder)
        
        # Create additional columns with placeholder (zero) values.
        for column in columns:
            if column in self.pop_data.columns:
                continue
            self.pop_data.loc[:, column] = 0.0

        self.max_age = builder.configuration.population.max_age

        self.start_year = builder.configuration.time.start.year
        self.clock = builder.time.clock()

        # Track all of the quantities that exist in the core spreadsheet table.
        builder.population.initializes_simulants(self.on_initialize_simulants, creates_columns=columns)
        self.population_view = builder.population.get_view(columns + ['tracked'])

        # Age cohorts before each time-step (except the first time-step).
        builder.event.register_listener('time_step__prepare', self.on_time_step_prepare)

    def on_initialize_simulants(self, _):
        """Initialize each cohort."""
        self.population_view.update(self.pop_data)

    def on_time_step_prepare(self, event):
        """Remove cohorts that have reached the maximum age."""
        pop = self.population_view.get(event.index, query='tracked == True')
        # Only increase cohort ages after the first time-step.
        if self.clock().year > self.start_year:
            pop['age'] += 1
        pop.loc[pop.age > self.max_age, 'tracked'] = False
        self.population_view.update(pop)


class Mortality:
    """
    This component reduces the population size of each cohort over time,
    according to the all-cause mortality rate.
    """
    
    @property
    def name(self):
        return 'mortality'

    def setup(self, builder):
        """Load the all-cause mortality rate."""
        mortality_agg = builder.data.load('mortality.agg')
        self.mortality_agg = builder.value.register_rate_producer(
            'mortality_agg', source=builder.lookup.build_table(
                mortality_agg, 
                key_columns=['sex'], 
                parameter_columns=['age','year']))
        
        mortality_prop = builder.data.load('mortality.prop')
        self.mortality_prop = builder.value.register_rate_producer(
            'mortality_prop', source=builder.lookup.build_table(
                mortality_prop, 
                key_columns=['sex', 'strata'], 
                parameter_columns=['age','year']))

        builder.event.register_listener('time_step', self.on_time_step)

        self.population_view = builder.population.get_view([
            'age', 'sex', 'strata',
            'population', 'bau_population', 'acmr', 'acmr_prop', 'bau_acmr',
            'pr_death', 'bau_pr_death', 'deaths', 'bau_deaths',
            'person_years', 'bau_person_years'])


    def population_state_timestep_2state(self, pop, rate):
        '''Computes new population(s) for end of the timestep assuming population(s) changes 
        according to two-state Markov process.
        '''
        new_pop =  pop*np.exp(-rate)
        return new_pop


    def get_subpop_rates_2state(self, agg_pop, agg_rate, sub_pops, rate_ratios):
        '''Returns transition rates for sub-populations for current timestep t assuming 
        sub-populations change according to two-state Markov process.
        '''
        if agg_rate == 0:
            return 0 * rate_ratios
        
        f = lambda x: np.sum(sub_pops*np.power(x,rate_ratios)) - self.population_state_timestep_2state(agg_pop, agg_rate)
        if f(0)*f(1) >= 0:
            pdb.set_trace()
        root = optimize.brentq(f,0,1)
        return -np.log(root)*rate_ratios


    def on_time_step(self, event):
        """
        Calculate the number of deaths and survivors at each time-step, for
        both the BAU and intervention scenarios.
        """
        pop = self.population_view.get(event.index)
        if pop.empty:
            return
        
        # Read in values that may be modified, as they are rate_producers.
        # Note that self.mortality_agg is only indexed by age and sex. This means that pop.acmr
        # is the acmr for the whole cohort, not yet seperated into strata.
        pop.acmr = self.mortality_agg(event.index)
        pop.acmr_prop = self.mortality_prop(event.index)
        
        # Sum over the population of the strata in each cohort, as we need to know total
        # population to work with total acmr.
        pop_agg = pop[['age', 'sex', 'population']].groupby(['sex', 'age']).sum().reset_index()
        
        # Note that acmr_prop only exists to make the following code work nicely.
        pop_prop = pop[['age', 'sex', 'strata', 'population', 'acmr', 'acmr_prop']]
        
        # TODO, vectorise this loop.
        for index, row in pop_agg.iterrows():
            # Find the strata data for this row of the aggregate population table.
            strata = pop_prop.loc[(pop_prop['age'] == row.age) & (pop_prop['sex'] == row.sex)]
            # Now the fact that acmr is not per strata comes into play, as we all we want is
            # the value for the cohort. We simply read it from the first strata with iloc[0].
            rates = self.get_subpop_rates_2state(
                row.population, strata['acmr'].iloc[0], 
                strata['population'], strata['acmr_prop'])
            
            # Overwrite the appropriate part of the stratified pop table with the calculated
            # rates. Each entry in the table is now the correct mortality rate.
            rates = rates.rename('acmr')
            pop_prop = pop_prop.merge(rates, how='left', left_index=True, right_index=True)
            pop_prop['acmr'] = pop_prop['acmr_y'].fillna(pop_prop['acmr_x'])
            pop_prop = pop_prop.drop(['acmr_x','acmr_y'], axis=1)
        
        # Write the correct acmr for each strata into the main pop table, then iterate the state
        # of each row of the table independently.
        pop.acmr = pop_prop.acmr
        probability_of_death = 1 - np.exp(-pop.acmr)
        deaths = pop.population * probability_of_death
        pop.population *= 1 - probability_of_death
        pop.pr_death = probability_of_death
        pop.deaths = deaths
        pop.person_years = pop.population + 0.5 * pop.deaths
        
        # BAU does not yet use the hetrogeneity code.
        pop.bau_acmr = self.mortality_agg.source(event.index)
        bau_probability_of_death = 1 - np.exp(-pop.bau_acmr)
        bau_deaths = pop.bau_population * bau_probability_of_death
        pop.bau_population *= 1 - bau_probability_of_death
        pop.bau_pr_death = bau_probability_of_death
        pop.bau_deaths = bau_deaths
        pop.bau_person_years = pop.bau_population + 0.5 * pop.bau_deaths
        self.population_view.update(pop)


class Disability:
    """
    This component calculates the health-adjusted life years (HALYs) for each
    cohort over time, according to the years lost due to disability (YLD)
    rate.
    """
    
    @property
    def name(self):
        return 'disability'

    def setup(self, builder):
        """Load the years lost due to disability (YLD) rate."""
        yld_agg = builder.data.load('yld.agg')
        self.yld_agg = builder.value.register_rate_producer(
            'yld_agg', source=builder.lookup.build_table(
                yld_agg, 
                key_columns=['sex'], 
                parameter_columns=['age','year']))
        
        yld_prop = builder.data.load('yld.prop')
        self.yld_prop = builder.value.register_rate_producer(
            'yld_prop', source=builder.lookup.build_table(
                yld_prop, 
                key_columns=['sex', 'strata'], 
                parameter_columns=['age','year']))

        builder.event.register_listener('time_step', self.on_time_step)

        self.population_view = builder.population.get_view([
            'age', 'sex', 'strata',
            'bau_yld_rate', 'yld_rate', 'yld_prop',
            'bau_person_years', 'person_years',
            'bau_HALY', 'HALY'])


    def disaggregate_YLD(self, agg_py, agg_yld, sub_py, sub_yld_ratios):
        '''Returns transition rates for sub-populations for current timestep t assuming 
        sub-populations change according to two-state Markov process.
        '''
        if agg_yld == 0:
            return 0 * sub_py
        
        ref_YLD = agg_py * agg_yld / np.sum(sub_yld_ratios * sub_py)
        # The following needs to be true
        # agg_py * (1 - agg_yld) == np.sum(sub_py * (1 - ref_YLD * sub_yld_ratios))
        return ref_YLD * sub_yld_ratios
    
    
    def on_time_step(self, event):
        """
        Calculate the HALYs for each cohort at each time-step, for both the
        BAU and intervention scenarios.
        """
        pop = self.population_view.get(event.index)
        if pop.empty:
            return
        
        # Note that self.yld_agg is only indexed by age and sex. It is not yet seperated into
        # strata.
        pop.yld_rate = self.yld_agg(event.index)
        pop.yld_prop = self.yld_prop(event.index)
        
        # Calculate lived person years for this time step for each strata.
        pop_agg = pop[['age', 'sex', 'person_years']].groupby(['sex', 'age']).sum().reset_index()
        
        # Note that yld_prop only exists to make the following code work nicely.
        pop_prop = pop[['age', 'sex', 'strata', 'person_years', 'yld_rate', 'yld_prop']]
        
        # TODO, vectorise this loop.
        for index, row in pop_agg.iterrows():
            # Find the strata data for this row of the aggregate population table.
            strata = pop_prop.loc[(pop_prop['age'] == row.age) & (pop_prop['sex'] == row.sex)]
            # Now the fact that yld_rate is not per strata comes into play, as we all we want is
            # the value for the cohort. We simply read it from the first strata with iloc[0].
            rates = self.disaggregate_YLD(
                row.person_years, strata['yld_rate'].iloc[0], 
                strata['person_years'], strata['yld_prop'])
            
            # Overwrite the appropriate part of the stratified pop table with the calculated
            # rates. Each entry in the table is now the correct mortality rate.
            rates = rates.rename('yld_rate')
            pop_prop = pop_prop.merge(rates, how='left', left_index=True, right_index=True)
            pop_prop['yld_rate'] = pop_prop['yld_rate_y'].fillna(pop_prop['yld_rate_x'])
            pop_prop = pop_prop.drop(['yld_rate_x','yld_rate_y'], axis=1)
        
        pop.yld_rate = pop_prop.yld_rate
        pop.HALY = pop.person_years * (1 - pop.yld_rate) 
            
        pop.bau_yld_rate = self.yld_agg.source(event.index)
        pop.bau_HALY = pop.bau_person_years * (1 - pop.bau_yld_rate)
        self.population_view.update(pop)
        