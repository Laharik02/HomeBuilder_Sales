-- Mart model -  business metric definitions
-- Selects from int_sales, adds more calculated metrics
-- Only model queried by the Streamlit dashboard

with joined as (

    select * from {{ ref('int_sales') }}

),

final as (

    select
        -- identifiers
        contract_id,

        -- location
        community,
        city,
        region,

        -- regional manager info
        regional_manager,
        sales_target_units,
        margin_target_pct,

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
        price_per_sqft,

        -- dates
        contract_date,
        close_date,
        days_to_close,
        year(contract_date)  as contract_year,
        month(contract_date) as contract_month,
        case 
            when month(contract_date) = 1 then 'January'
            when month(contract_date) = 2 then 'February'
            when month(contract_date) = 3 then 'March'
            when month(contract_date) = 4 then 'April'
            when month(contract_date) = 5 then 'May'
            when month(contract_date) = 6 then 'June'
            when month(contract_date) = 7 then 'July'
            when month(contract_date) = 8 then 'August'
            when month(contract_date) = 9 then 'September'
            when month(contract_date) = 10 then 'October'
            when month(contract_date) = 11 then 'November'
            when month(contract_date) = 12 then 'December'
        end as contract_month_name,

        -- status flags
        status,
        is_cancelled,
        is_closed,
        is_under_contract,

        -- contract outcome label
        case
            when is_cancelled then 'Cancelled'
            when is_closed then 'Closed'
            else 'In Progress'
        end as contract_outcome,

        -- lead source
        buyer_source,
        loan_type,

        -- sales rep
        sales_consultant,
        agent_commission,

        -- metric 1: incentive intensity ratio
        -- flags margin leakage — high ratio means deals are being discounted to close
        round(
            incentive_amount / nullif(contract_price, 0) * 100, 2
        ) as incentive_intensity_pct,

        -- metric 2: commission efficiency
        -- cost of external realtor support as % of contract price
        round(
            agent_commission / nullif(contract_price, 0) * 100, 2
        ) as commission_efficiency_pct,

        -- metric 3: buyer source effectiveness building blocks
        -- dashboard aggregates these by buyer_source to calculate cancellation rate
        case when is_cancelled then 1 else 0 end as cancelled_unit,
        case when is_closed then 1 else 0 end as net_closed_unit,

        -- metric 4: target attainment
        -- ties each deal back to regional manager targets
        sales_target_units as regional_unit_target,
        round(
            margin_target_pct * contract_price, 2
        ) as implied_margin_target_dollars,

        -- metric 5: net value added per deal
        -- upgrade revenue minus incentive giveaway
        (upgrade_amount - incentive_amount) as net_value_added

    from joined

)

select * from final
