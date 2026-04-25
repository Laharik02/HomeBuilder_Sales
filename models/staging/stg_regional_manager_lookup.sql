with source as (

    select * from {{ source('raw', 'REGIONAL_MANAGER_LOOKUP') }}

),

renamed as (

    select
        -- region identifier (this is the join key to sales data)
        region,

        -- manager info
        regional_manager,

        -- targets
        sales_target_units,
        margin_target_pct

    from source

)

select * from renamed