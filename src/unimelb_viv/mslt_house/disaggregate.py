
def disaggregate_pop(pop, scalarName, rateName, propName,
                     pop_agg_src, pop_prop_src, disaggregate_func):
    """
    Disaggregate the population, returning a 'rateName' column with the disaggregated populations
    for each strata of each cohort.

    ``pop``
        A view of the population table.
    ``scalarName``
        The name of the scalar in pop (eg 'population') to disaggregate over.
    ``rateName``
        The name of the rate in pop to apply to the scalar. This can be a risk or a rate in
        practise, as updating pop[scalarName] based on pop[rateName] is done elsewhere.
    ``propName``
        The name of rate ratio for each strata in pop.
    ``pop_agg_src``
        The source of the aggregate rate for the aggregate pop of the cohort. This will often
        come from a rate_producer such as 'self.mortality_agg(event.index)'.
    ``pop_prop_src``
        The source of the rate ratios for each strata in each cohort. This will often come
        from a rate_producer such as 'self.mortality_prop(event.index)'. 
    ``disaggregate_func``
        The underlying function that disaggregates the population. It is called once for each
        cohort. Its arguments are as follows.
            - The 'scalarName' size of the cohort.
            - The 'rateName' rate that acts on the whole cohort.
            - The 'scalarName' sizes of each of the strata in the cohort. This sums to the
                first argument.
            - The 'propName' rate ratios for strata in the cohort.

    """
    # Read in values that may be modified, as they are rate_producers.
    # Note that pop_agg is only indexed by age and sex. This means that pop_agg['rateName']
    # is the rate for the whole cohort, not yet seperated into strata.
    pop[rateName] = pop_agg_src
    pop[propName] = pop_prop_src
    
    # Sum over the population of the strata in each cohort, as we need to know total
    # of the scalar for the disaggregation.
    pop_agg = pop[['age', 'sex', scalarName]].groupby(['sex', 'age']).sum().reset_index()
    
    # Note that propName only exists to make the following code work nicely. It is an intermediate
    # value that can be used by multiple disaggregate_pop calls.
    pop_prop = pop[['age', 'sex', 'strata', scalarName, rateName, propName]]
    
    # TODO, vectorise this loop.
    for index, row in pop_agg.iterrows():
        # Find the strata data for this row of the aggregate population table.
        strata = pop_prop.loc[(pop_prop['age'] == row.age) & (pop_prop['sex'] == row.sex)]
        # Now the fact that acmr is not per strata comes into play, as we all we want is
        # the value for the cohort. We simply read it from the first strata with iloc[0].
        rates = disaggregate_func(
            row[scalarName], strata[rateName].iloc[0], 
            strata[scalarName], strata[propName])
        # Overwrite the appropriate part of the stratified pop table with the calculated
        # rates. Each entry in the table is now the correct mortality rate.
        rates = rates.rename(rateName)
        pop_prop = pop_prop.merge(rates, how='left', left_index=True, right_index=True)
        pop_prop[rateName] = pop_prop[rateName + '_y'].fillna(pop_prop[rateName + '_x'])
        pop_prop = pop_prop.drop([rateName + '_x', rateName + '_y'], axis=1)
   
    return pop_prop[rateName]