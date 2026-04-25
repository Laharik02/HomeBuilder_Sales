with 

source as (

    select * from {{ source('raw', 'HOMEBUILDER_SALES') }}

),

renamed as (

    select
        contract_id,
        community,
        city,
        region,
        plan_name,
        sqft,
        bedrooms,
        bathrooms,
        base_price,
        upgrade_amount,
        incentive_amount,
        contract_price,
        contract_date,
        close_date,
        days_to_close,
        status,
        buyer_source,
        agent_commission,
        loan_type,
        sales_consultant

    from source

)

select * from renamed