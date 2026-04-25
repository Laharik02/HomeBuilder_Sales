with sales as (

    select * from {{ ref('stg_homebuilder_sales') }}

),

managers as (

    select * from {{ ref('stg_regional_manager_lookup') }}

),

joined as (

    select
        -- identifiers
        sales.contract_id,

        -- location
        sales.community,
        sales.city,
        sales.region,

        -- regional manager info (joined from lookup table)
        managers.regional_manager,
        managers.sales_target_units,
        managers.margin_target_pct,

        -- product
        sales.plan_name,
        sales.sqft,
        sales.bedrooms,
        sales.bathrooms,

        -- pricing
        sales.base_price,
        sales.upgrade_amount,
        sales.incentive_amount,
        sales.contract_price,
        sales.price_per_sqft,

        -- dates
        sales.contract_date,
        sales.close_date,
        sales.days_to_close,

        -- status flags
        sales.status,
        sales.is_cancelled,
        sales.is_closed,
        sales.is_under_contract,

        -- lead source
        sales.buyer_source,
        sales.loan_type,

        -- sales rep
        sales.sales_consultant,
        sales.agent_commission

    from sales
    left join managers
        on sales.region = managers.region

)

select * from joined