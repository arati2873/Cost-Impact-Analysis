 
# Define SKU limits
BASIC_SKU_LIMIT = 3000000
IS_PRO_VERSION = False  # Set to True for Pro version

    
# --- Streamlit App: Price Revision Tool ---
import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.express as px
#from sklearn.preprocessing import MinMaxScaler

#Stage 5 Complete:Product Group and family level summary with override option
# Set up page
st.set_page_config(page_title="Smart Pricing", layout="wide")
st.title("📈 Cost Increase Impact Analysis")

st.info("🔒 Your data is not stored or shared. Files are processed securely within your session for analysis only.")

st.sidebar.markdown("[🛒 Buy Access - $99](https://yadavarati.gumroad.com/l/IntelligentPriceRevisionTool)")

# --- Access Gate ---
ACCESS_CODE = "A"

with st.expander("🔐 Enter Access Code to Unlock the Tool"):
    user_code = st.text_input("Access Code", type="password")

if user_code != ACCESS_CODE:
    st.warning("This is a premium tool. Please enter a valid access code to continue.")
    st.stop()


with st.expander("❓ How to Use This Tool (Click to Expand)"):
    st.markdown("""
    ### 📘 Required Inputs
    This tool requires 6 CSV files:
    1. **cost_file.csv** – Cost data by SKU
    2. **sales_ytd.csv** – Recent sales data (e.g., last 6 months or 1 year)
    3. **product_classification.csv** – Classification mapping (Family, Group, etc.)

    ➡️ Make sure **column headers are not changed** from the provided templates.

    ---

    ### ⚙️ How It Works
    - Upload all required files from the sidebar
    - Download cost impact summary

    ---

    📂 You can [download sample input files here](https://github.com/arati2873/Cost-Impact-Analysis)

    📄 Full user guide available in the [README](https://github.com/arati2873/Cost-Impact-Analysis/blob/main/README.md.txt)
    """)



# Step 1: Upload files
st.sidebar.markdown("### 📤 Upload Required Files")

uploaded_files = {
    "Cost File": st.sidebar.file_uploader("Upload cost_file.csv", type="csv"),
    "Sales YTD": st.sidebar.file_uploader("Upload sales_ytd.csv", type="csv"),
    "Product Classification": st.sidebar.file_uploader("Upload product_classification.csv", type="csv")
}

if all(uploaded_files.values()):
    data_loaded = True
    file_paths = uploaded_files
else:
    #st.warning("⚠️ Please upload all five input files to continue.")
    data_loaded = False


def summarize_revenue(df, group_col):
    summary = df.groupby(group_col).agg(
        Total_Revenue_Old=('Revenue_1', 'sum'),
        Total_Revenue_New=('New_Revenue', 'sum'),
        TTL_Cost=('TTL_Cost', 'sum'),
        New_Cost=('New_Cost', 'sum')
    ).reset_index()

    summary['Revenue_Increase_%'] = (
        (summary['Total_Revenue_New'] - summary['Total_Revenue_Old']) / summary['Total_Revenue_Old']
    ) * 100

    summary['Cost_Increase_%'] = (
        (summary['New_Cost'] - summary['TTL_Cost']) / summary['TTL_Cost']
    ) * 100

    summary['Old_GM'] = summary['Total_Revenue_Old'] - summary['TTL_Cost']
    summary['New_GM'] = summary['Total_Revenue_New'] - summary['New_Cost']
    summary['GM_Impact'] = summary['New_GM'] - summary['Old_GM']
    summary['Old_GM%'] = (summary['Old_GM'] / summary['Total_Revenue_Old']) * 100
    summary['New_GM%'] = (summary['New_GM'] / summary['Total_Revenue_New']) * 100

    return summary



# --- Main Logic ---
# 🧼 Sanitize all inputs
def clean_column_names(df):
    df.columns = df.columns.str.strip()
    return df

def clean_sku_column(df):
    df['SKU'] = df['SKU'].astype(str).str.strip().str.upper()
    return df

def clean_numeric_column(df, col):
    df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

if data_loaded:
    cost_df = clean_column_names(pd.read_csv(file_paths["Cost File"]))
    sales_1 = clean_column_names(pd.read_csv(file_paths["Sales YTD"]))
    product_class = clean_column_names(pd.read_csv(file_paths["Product Classification"]))

    # 🧼 Clean SKU
    for df in [cost_df, sales_1, product_class]:
        df = clean_sku_column(df)

    # ✅ Merge
    df = sales_1.merge(cost_df, on='SKU', how='left')
    df = df.merge(product_class, on='SKU', how='left')

    # 🧼 Ensure numeric
    #numeric_cols = ['Revenue_1', 'Revenue_2', 'GM%_1', 'GM%_2', 'GM_1', 'GM_2', 'ASP_1', 'ASP_2','TTL_Cost','Qty','Cost_per_Unit']
    #for col in numeric_cols:
     #   df = clean_numeric_column(df, col)
    
    sku_count = df['SKU'].nunique()

    if not IS_PRO_VERSION and sku_count > BASIC_SKU_LIMIT:
        st.error(f"❌ You've exceeded the 30,000 SKU limit. Please upgrade to the Pro version.")
        st.stop()
    
    st.sidebar.markdown("### Inventory & Sales Coverage")

    total_months = st.sidebar.number_input("Total Months of Sales Data", min_value=1, max_value=36, value=6)
    stock_months = st.sidebar.number_input("Months Worth of Stock Available", min_value=0, max_value=12, value=0)
    # Impact fraction (sales affected by new price)
    impact_fraction = max((total_months - stock_months) / total_months, 0)
    
        # Clean and convert relevant columns to numeric
    df['TTL_Cost'] = pd.to_numeric(df['TTL_Cost'], errors='coerce')
    df['Cost_Change_%'] = pd.to_numeric(df['Cost_Change_%'], errors='coerce')
    df['Revenue_1'] = pd.to_numeric(df['Revenue_1'], errors='coerce')
    df['GM_1'] = pd.to_numeric(df['GM_1'], errors='coerce')


      # Impact fraction (sales affected by new price)
    #impact_fraction = max((total_months - stock_months) / total_months, 0)

    # Split revenue & cost into impacted vs non-impacted
    df['Impacted_Revenue'] = df['Revenue_1'] * impact_fraction
    df['Non_Impacted_Revenue'] = df['Revenue_1'] * (1 - impact_fraction)

    df['Impacted_Cost'] = df['TTL_Cost'] * impact_fraction
    df['Non_Impacted_Cost'] = df['TTL_Cost'] * (1 - impact_fraction)

    # Apply price / cost change ONLY on impacted portion
    df['New_Revenue'] = (
        df['Non_Impacted_Revenue'] +
        df['Impacted_Revenue'] * (1 + df['Cost_Change_%'] / 100)
    )

    df['New_Cost'] = (
        df['Non_Impacted_Cost'] +
        df['Impacted_Cost'] * (1 + df['Cost_Change_%'] / 100)
    )


         

    full_summary = summarize_revenue(df,'Product_Family')

    total_row = pd.DataFrame({
        'Product_Family': ['TOTAL'],
        'Total_Revenue_Old': [df['Revenue_1'].sum()],
        'Total_Revenue_New': [df['New_Revenue'].sum()],
        'TTL_Cost': [df['TTL_Cost'].sum()],
        'New_Cost': [df['New_Cost'].sum()]
    })
    
    total_row['Old_GM%'] = (
        (total_row['Total_Revenue_Old'] - total_row['TTL_Cost']) / total_row['Total_Revenue_Old']
    ) * 100

    total_row['Revenue_Increase_%'] = (
        (total_row['Total_Revenue_New'] - total_row['Total_Revenue_Old']) / total_row['Total_Revenue_Old']
    ) * 100

    total_row['Cost_Increase_%'] = (
        (total_row['New_Cost'] - total_row['TTL_Cost']) / total_row['TTL_Cost']
    ) * 100

    total_row['Old_GM'] = total_row['Total_Revenue_Old'] - total_row['TTL_Cost']
    total_row['New_GM'] = total_row['Total_Revenue_New'] - total_row['New_Cost']
    total_row['New_GM%'] = (
        (total_row['Total_Revenue_New'] - total_row['New_Cost']) / total_row['Total_Revenue_New']
    ) * 100
    total_row['GM_Impact'] = total_row['New_GM'] - total_row['Old_GM']
    


    full_summary = pd.concat([summarize_revenue(df,'Product_Family'), total_row], ignore_index=True)

    for col in ['Total_Revenue_Old', 'Total_Revenue_New', 'TTL_Cost', 'New_Cost', 'Old_GM', 'New_GM', 'GM_Impact']:
        full_summary[col] = full_summary[col].round(0).apply(lambda x: f"{x:,.0f}")

    for col in ['Revenue_Increase_%', 'Cost_Increase_%','Old_GM%','New_GM%']:
        full_summary[col] = full_summary[col].round(2)


    #full_summary['Revenue_Increase_%'] = full_summary['Revenue_Increase_%'].round(2)
    #full_summary['Cost_Increase_%'] = full_summary['Cost_Increase_%'].round(2)

    st.subheader("📊 Summary of Cost Increase Impact")
    st.dataframe(full_summary, use_container_width=True)
    
    # Product Group Summary
    product_group_summary = summarize_revenue(df, 'Product_Group')

    # Format numbers
    for col in ['Total_Revenue_Old', 'Total_Revenue_New', 'TTL_Cost', 'New_Cost', 'Old_GM', 'New_GM','GM_Impact']:
        product_group_summary[col] = product_group_summary[col].round(0).apply(lambda x: f"{x:,.0f}")
    product_group_summary['Revenue_Increase_%'] = product_group_summary['Revenue_Increase_%'].round(2)
    product_group_summary['Cost_Increase_%'] = product_group_summary['Cost_Increase_%'].round(2)
    product_group_summary['Old_GM%'] = product_group_summary['Old_GM%'].round(2)
    product_group_summary['New_GM%'] = product_group_summary['New_GM%'].round(2)

    # Display it
    st.subheader("📘 Product Group Level Summary")
    st.dataframe(product_group_summary, use_container_width=True)
    
    #import plotly.express as px

    # --------------------------------------------
    # CLEAN & PREPARE full_summary FOR VISUALIZATION
    # --------------------------------------------
    viz_df = full_summary[full_summary['Product_Family'] != 'TOTAL'].copy()

    # Ensure revenue and GM columns are numeric
    cols_to_convert = ['Total_Revenue_Old', 'Total_Revenue_New']
    for col in cols_to_convert:
        viz_df[col] = viz_df[col].replace(',', '', regex=True).astype(float)

    # Sort by old revenue
    viz_df = viz_df.sort_values(by='Total_Revenue_Old')

    # --------------------------------------------
    # 1️⃣ Revenue Before vs After (Grouped Bar)
    # --------------------------------------------
    import plotly.graph_objects as go

    # Melt revenue values
    melted = viz_df.melt(
        id_vars='Product_Family',
        value_vars=['Total_Revenue_Old', 'Total_Revenue_New'],
        var_name='Revenue Type',
        value_name='Amount'
    )

    # Create the figure
    fig1 = go.Figure()

    # Add grouped bar for revenue
    for revenue_type in melted['Revenue Type'].unique():
        data = melted[melted['Revenue Type'] == revenue_type]
        fig1.add_trace(go.Bar(
            x=data['Product_Family'],
            y=data['Amount'],
            name=revenue_type,
            yaxis='y1'
        ))

    # Add line for Assigned Price Increase %
    fig1.add_trace(go.Scatter(
        x=viz_df['Product_Family'],
        y=viz_df['Revenue_Increase_%'],
        name='Assigned Price Increase %',
        mode='lines+markers',
        yaxis='y2',
        line=dict(color='crimson', width=3, dash='dash')
    ))

    # Update layout for dual axis
    fig1.update_layout(
        title=' Revenue Before vs After Price Revision +  Assigned Price Increase %',
        xaxis=dict(title='Product Family'),
        yaxis=dict(
            title='Revenue (AED)',
            side='left'
        ),
        yaxis2=dict(
            title='Assigned Price Increase (%)',
            overlaying='y',
            side='right',
            showgrid=False
        ),
        barmode='group',
        xaxis_tickangle=-45,
        legend=dict(x=0.01, y=1.1, orientation='h'),
        margin=dict(t=60)
    )

    # Display in Streamlit
    st.plotly_chart(fig1, use_container_width=True)


    # --------------------------------------------
    # 3️⃣ Price Increase % Distribution (Histogram)
    # --------------------------------------------
    fig3 = px.histogram(
        df,
        x='Cost_Change_%',
        nbins=20,
        title='📈 Distribution of Assigned Price Increase %',
        labels={'Cost_Change_%': 'Price Increase (%)'}
    )
    st.plotly_chart(fig3, use_container_width=True)

    
     # 5️⃣ Revenue Curve vs Price Increase %
    # --------------------------------------------
    fig5 = px.scatter(
        df,
        x='Cost_Change_%',
        y='New_Revenue',
        size='Revenue_1',
        color='Product_Family',
        title='📈 Revenue Curve by Price Increase %',
        labels={
            'Cost_Change_%': 'Price Increase (%)',
            'New_Revenue': 'Estimated New Revenue',
            'Revenue_1': 'Base Revenue'
        },
        hover_data=['SKU','Cost_Change_%']
    )
    fig5.update_traces(marker=dict(opacity=0.7, line=dict(width=0.5, color='gray')))
    st.plotly_chart(fig5, use_container_width=True)

    # ⬇️ Download CSV with all scoring logic

# Convert DataFrames to CSV
    pm_csv = full_summary.to_csv(index=False)
    pg_csv = product_group_summary.to_csv(index=False)

    st.download_button(
        label="📥 Product summary by Product Family",
        data=pm_csv,
        file_name="PM_Summary.csv",
        mime="text/csv"
    )

    st.download_button(
        label="📥 Product summary by Product Group",
        data=pg_csv,
        file_name="PG_Summary.csv",
        mime="text/csv"
    )




else:
    st.warning("⚠️ Please upload all three input files to start.")