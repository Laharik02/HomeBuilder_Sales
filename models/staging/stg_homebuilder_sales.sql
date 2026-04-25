with source as (

    select * from {{ source('raw', 'HOMEBUILDER_SALES') }}

),

renamed as (

    select
        -- identifiers
        contract_id,

        -- location
        community,
        city,
        region,

        -- product
        plan_name,
        sqft,
        bedrooms,
        bathrooms,

        -- pricing
        base_price,
        upgrade_amount,
        incentive_amount,
        contract_price,

        -- calculated price metric
        round(contract_price / nullif(sqft, 0), 2) as price_per_sqft,

        -- dates
        contract_date,
        close_date,

        -- days to close is null for cancelled and in-progress deals
        days_to_close,

        -- status & categorization
        status,
        case when status = 'Cancelled' then true else false end as is_cancelled,
        case when status = 'Closed' then true else false end as is_closed,
        case when status = 'Under Contract' then true else false end as is_under_contract,

        -- lead source
        buyer_source,
        loan_type,

        -- sales
        sales_consultant,

        -- casting to integer since commission is always whole dollars
        -- 117 records have zero commission (walk-in deals with no agent)
        cast(agent_commission as integer) as agent_commission

    from source

)

select * from renamed