
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import time
import os
import openpyxl
from datetime import datetime
import altair as alt
import math

from supabase import create_client, Client
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except KeyError as e:
    st.error(f"Supabase secret not found: {e}. Please ensure you have configured .streamlit/secrets.toml correctly.")
    st.stop()

st.set_page_config(
    page_title="Single-File Multi-Page App",
    page_icon="📄",
    layout="wide")
def home_page():
    """Displays the home page content."""
    st.title("DXC-HPI Reporting Tool")
    st.write("Summary of Pages")
    st.markdown(
        """
        Page 1: Input Tickets for Badging Dispatches
        """)
    st.markdown(
        """
        Page 2: Input Tickets for Actual Dispatches
        """)
    st.markdown(
        """
        Page 3: Report on Badge Pickup Budget
        """)
    st.markdown(
        """
        Page 4: Report on PNL
        """)
    st.markdown("<br>" * 12, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.image("suryl_logo_rgb.png", width=500)

def PAGE_1():
    st.title("Badging Ticket Dispatches")
    st.write("View, filter, and add your badging tickets.")
    EDITABLE_DISPLAY_COLUMNS = ["Date", "Tech", "Site", "Hours", "Additional", "Base", "Total"]
    ALL_DISPLAY_COLUMNS = EDITABLE_DISPLAY_COLUMNS
    @st.cache_data(ttl="1h")
    def load_badging_data():
        try:
            response = supabase.table("badging_dispatches").select("*").order("Date", desc=False).execute()
            data = response.data
            if data:
                df_loaded = pd.DataFrame(data)
                for col in ALL_DISPLAY_COLUMNS:
                    if col not in df_loaded.columns:
                        if col in ["Hours", "Additional", "Base", "Total"]:
                            df_loaded[col] = 0.0
                        elif col == "Date":
                            df_loaded[col] = pd.NaT
                        else:
                            df_loaded[col] = ""
                if "Date" in df_loaded.columns:
                    df_loaded["Date"] = pd.to_datetime(df_loaded["Date"], errors='coerce')
                for col in ["Hours", "Additional", "Base", "Total"]:
                    if col in df_loaded.columns:
                        df_loaded[col] = pd.to_numeric(df_loaded[col], errors='coerce').fillna(0.0)
                for col in df_loaded.columns:
                    if col not in ["id", "Date", "Hours", "Additional", "Base", "Total"]:
                        df_loaded[col] = df_loaded[col].astype(str)
                return df_loaded[ALL_DISPLAY_COLUMNS] 
            else:
                st.info("No data found in 'badging_dispatches' table. Starting with an empty table.")
                empty_df = pd.DataFrame(columns=ALL_DISPLAY_COLUMNS)
                empty_df["id"] = pd.Series(dtype='int64') 
                empty_df["Date"] = pd.to_datetime(pd.Series(dtype='datetime64[ns]'))
                for col in ["Hours", "Additional", "Base", "Total"]:
                    empty_df[col] = pd.Series(dtype='float64')
                return empty_df
        except Exception as e:
            st.error(f"Error loading data from Supabase: {e}")
            st.warning("Displaying an empty DataFrame due to loading error.")
            empty_df = pd.DataFrame(columns=ALL_DISPLAY_COLUMNS)
            empty_df["id"] = pd.Series(dtype='int64')
            empty_df["Date"] = pd.to_datetime(pd.Series(dtype='datetime64[ns]'))
            for col in ["Hours", "Additional", "Base", "Total"]:
                empty_df[col] = pd.Series(dtype='float64')
            return empty_df
    if 'df_badging_page1' not in st.session_state:
        st.session_state.df_badging_page1 = load_badging_data()
    st.header("Existing Badging Tickets")
    column_configuration = {
        "id": st.column_config.NumberColumn(
            "ID",
            disabled=True,
            width="small"),
        "Date": st.column_config.DateColumn(
            "Date",
            format="YYYY-MM-DD",
            required=True),
        "Hours": st.column_config.NumberColumn(
            "Hours",
            min_value=0.00,
            format="%.2f"),
        "Additional": st.column_config.NumberColumn(
            "Additional Pay ($)",
            min_value=0.00,
            format="dollar"),
        "Base": st.column_config.NumberColumn(
            "Base Pay ($)",
            min_value=0.00,
            format="dollar"),
        "Total": st.column_config.NumberColumn(
            "Total Pay ($)",
            min_value=0.00,
            format="dollar")}
    for col in EDITABLE_DISPLAY_COLUMNS:
        if col not in column_configuration:
            column_configuration[col] = st.column_config.TextColumn(col)
    edited_df = st.data_editor(
        st.session_state.df_badging_page1,
        num_rows="fixed",
        use_container_width=True,
        key="data_editor_badging_page1",
        column_config=column_configuration,
        column_order=ALL_DISPLAY_COLUMNS)
    if not edited_df.equals(st.session_state.df_badging_page1):
        st.session_state.df_badging_page1 = edited_df
        st.warning("Data in the table has been modified. Click 'Save All Changes to Supabase' to persist.")
    if st.button("Save All Changes to Supabase"):
        try:
            changes = st.session_state["data_editor_badging_page1"]["edited_rows"]
            if changes:
                for row_idx, updated_values in changes.items():
                    row_id = st.session_state.df_badging_page1.loc[row_idx, 'id']
                    data_to_update = {}
                    for col, value in updated_values.items():
                        if col == "Date":
                            data_to_update[col] = value.strftime('%Y-%m-%d') if pd.notna(value) else None
                        elif col in ["Hours", "Additional", "Base", "Total"]:
                            data_to_update[col] = float(value)
                        else:
                            data_to_update[col] = str(value)
                    response = supabase.table("badging_dispatches").update(data_to_update).eq("id", row_id).execute()
                    if response.data:
                        st.success(f"Row with ID {row_id} updated successfully!")
                    else:
                        st.error(f"Failed to update row {row_id}: {response.status_code} - {response.status_code}")
            else:
                st.info("No changes detected in the table to save.")
            load_badging_data.clear()
            if 'df_badging_page1' in st.session_state:
                del st.session_state.df_badging_page1
            st.rerun()
        except Exception as e:
            st.error(f"An error occurred while saving changes to Supabase: {e}")
    st.markdown("---")
    st.header("Add New Badging Ticket")
    @st.cache_data(ttl="1h")
    def load_tech_site_data():
        try:
            response = supabase.table("names_and_sites").select("Name, Site").execute()
            data = response.data
            if data:
                df_names_sites = pd.DataFrame(data)
                tech_names = sorted(df_names_sites['Name'].unique().tolist())
                site_names = sorted(df_names_sites['Site'].unique().tolist())
                return tech_names, site_names
            return [], []
        except Exception as e:
            st.error(f"Error loading Tech and Site data: {e}")
            return [], []
    tech_options, site_options = load_tech_site_data()
    with st.form("new_badging_ticket_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            new_date = st.date_input("Date:", value=datetime.today(), key="form_new_date")
            selected_tech = st.selectbox("Tech:", options=[""] + tech_options, index=0, key="form_new_tech_select")
            new_hours = st.number_input("Hours:", value=0.0, min_value=0.0, format="%.2f", key="form_new_hours")
            new_base = st.number_input("Base ($):", value=0.0, min_value=0.0, format="%.2f", key="form_new_base")
        with col2:
            selected_site = st.selectbox("Site:", options=[""] + site_options, index=0, key="form_new_site_select")
            new_additional = st.number_input("Additional ($):", value=0.0, min_value=0.0, format="%.2f", key="form_new_additional")
            calculated_total = new_base + new_additional
        add_button = st.form_submit_button("Add New Ticket")
        if add_button:
            new_row_data = {
                "Date": new_date.strftime('%Y-%m-%d'),
                "Tech": selected_tech,
                "Site": selected_site,
                "Hours": new_hours,
                "Additional": new_additional,
                "Base": new_base,
                "Total": calculated_total}
            try:
                response = supabase.table("badging_dispatches").insert([new_row_data]).execute()
                if response.data:
                    st.success("New ticket added to Supabase successfully!")
                    load_badging_data.clear()
                    if 'df_badging_page1' in st.session_state:
                        del st.session_state.df_badging_page1
                    st.rerun()
                else:
                    st.error(f"Failed to add new ticket: {response.status_code} - {response.status_code}")
            except Exception as e:
                st.error(f"An error occurred while adding new ticket: {e}")



def load_tech_site_data():
    try:
        response = supabase.table("names_and_sites").select("Name, Site").execute()
        data = response.data
        if data:
            df_names_sites = pd.DataFrame(data)
            tech_names = sorted(df_names_sites['Name'].unique().tolist())
            site_names = sorted(df_names_sites['Site'].unique().tolist())
            return tech_names, site_names
        return [], []
    except Exception as e:
        st.error(f"Error loading Tech and Site data: {e}")
        return [], []


def PAGE_2():
    st.title("Live Ticket Dispatches")
    st.write("View, filter, and add your live dispatches.")
    EDITABLE_DISPLAY_COLUMNS = ["Date", "Tech", "SLA", "Site", "Hours"]
    ALL_LIVE_DISPATCHES_COLUMNS = [
        "Date", "Tech", "SLA", "Site", "Hours", 
        "Rounded Hours", "Additional", "Base", "DXC Rate", "Total FN Pay", "Total DXC Pay", "PNL"]
    @st.cache_data(ttl="1h")
    def load_live_dispatches_data():
        try:
            response = supabase.table("live_dispatches").select("*").order("Date", desc=False).execute()
            data = response.data
            if data:
                df_loaded = pd.DataFrame(data)
                for col in ALL_LIVE_DISPATCHES_COLUMNS:
                    if col not in df_loaded.columns:
                        if col in ["Hours", "Rounded Hours", "Additional", "Base", "DXC Rate", "Total FN Pay", "Total DXC Pay", "PNL"]:
                            df_loaded[col] = 0.0
                        elif col == "Date":
                            df_loaded[col] = pd.NaT
                        else:
                            df_loaded[col] = ""
                if "Date" in df_loaded.columns:
                    df_loaded["Date"] = pd.to_datetime(df_loaded["Date"], errors='coerce')
                numeric_cols = ["Hours", "Rounded Hours", "Additional", "Base", "DXC Rate", "Total FN Pay", "Total DXC Pay", "PNL"]
                for col in numeric_cols:
                    if col in df_loaded.columns:
                        df_loaded[col] = pd.to_numeric(df_loaded[col], errors='coerce').fillna(0.0)
                if "SLA" in df_loaded.columns:
                    df_loaded["SLA"] = df_loaded["SLA"].astype(str)
                for col in df_loaded.columns:
                    if col not in ["ID", "Date"] + numeric_cols + ["SLA"]:
                        df_loaded[col] = df_loaded[col].astype(str)
                return df_loaded[ALL_LIVE_DISPATCHES_COLUMNS]
            else:
                st.info("No data found in 'live_dispatches' table. Starting with an empty table.")
                empty_df = pd.DataFrame(columns=ALL_LIVE_DISPATCHES_COLUMNS)
                empty_df["ID"] = pd.Series(dtype='int64')
                empty_df["Date"] = pd.to_datetime(pd.Series(dtype='datetime64[ns]'))
                for col in ["Hours", "Rounded Hours", "Additional", "Base", "DXC Rate", "Total FN Pay", "Total DXC Pay", "PNL"]:
                    empty_df[col] = pd.Series(dtype='float64')
                empty_df["SLA"] = pd.Series(dtype='object')
                return empty_df
        except Exception as e:
            st.error(f"Error loading data from Supabase: {e}")
            st.warning("Displaying an empty DataFrame due to loading error.")
            empty_df = pd.DataFrame(columns=ALL_LIVE_DISPATCHES_COLUMNS)
            empty_df["id"] = pd.Series(dtype='int64')
            empty_df["Date"] = pd.to_datetime(pd.Series(dtype='datetime64[ns]'))
            for col in ["Hours", "Rounded Hours", "Additional", "Base", "DXC Rate", "Total FN Pay", "Total DXC Pay", "PNL"]:
                empty_df[col] = pd.Series(dtype='float64')
            empty_df["SLA"] = pd.Series(dtype='object')
            return empty_df
    if 'df_live_dispatches_page2' not in st.session_state:
        st.session_state.df_live_dispatches_page2 = load_live_dispatches_data()
    st.header("Existing Live Dispatches")
    column_configuration = {
        "ID": st.column_config.NumberColumn(
            "ID",
            disabled=True,
            width="small"),
        "Date": st.column_config.DateColumn(
            "Date",
            format="YYYY-MM-DD",
            required=True,
            disabled=False),
        "Tech": st.column_config.TextColumn(
            "Tech",
            disabled=False),
        "Site": st.column_config.TextColumn(
            "Site",
            disabled=False),
        "SLA": st.column_config.TextColumn(
            "SLA",
            disabled=False),
        "Hours": st.column_config.NumberColumn(
            "Hours",
            min_value=0.00,
            format="%.2f",
            disabled=False),
        "Rounded Hours": st.column_config.NumberColumn(
            "Rounded Hours",
            min_value=0.00,
            format="%.2f",
            disabled=True),
        "Additional": st.column_config.NumberColumn(
            "Additional ($)",
            min_value=0.00,
            format="dollar",
            disabled=True),
        "Base": st.column_config.NumberColumn(
            "Base ($)",
            min_value=0.00,
            format="dollar",
            disabled=True),
        "DXC Rate": st.column_config.NumberColumn(
            "DXC Rate ($)",
            min_value=0.00,
            format="dollar",
            disabled=True),
        "Total FN Pay": st.column_config.NumberColumn(
            "Total FN Pay ($)",
            format="dollar",
            disabled=True),
        "Total DXC Pay": st.column_config.NumberColumn(
            "Total DXC Pay ($)",
            format="dollar",
            disabled=True),
        "PNL": st.column_config.NumberColumn(
            "P&L ($)",
            format="dollar",
            disabled=True),}
    edited_df = st.data_editor(
        st.session_state.df_live_dispatches_page2,
        num_rows="fixed",
        use_container_width=True,
        key="data_editor_live_dispatches_page2",
        column_config=column_configuration,
        column_order=ALL_LIVE_DISPATCHES_COLUMNS)
    if not edited_df.equals(st.session_state.df_live_dispatches_page2):
        st.session_state.df_live_dispatches_page2 = edited_df
        st.warning("Data in the table has been modified. Click 'Save All Changes to Supabase' to persist.")
    if st.button("Save All Changes to Supabase (Live Dispatches)"):
        try:
            changes = st.session_state["data_editor_live_dispatches_page2"]["edited_rows"]
            if changes:
                for row_idx, updated_values in changes.items():
                    row_id = st.session_state.df_live_dispatches_page2.loc[row_idx, 'id']
                    data_to_update = {}
                    for col, value in updated_values.items():
                        if col == "Date":
                            data_to_update[col] = value.strftime('%Y-%m-%d') if pd.notna(value) else None
                        elif col in ["Hours"]:
                            data_to_update[col] = float(value)
                        elif col in ["SLA", "Tech", "Site"]:
                            data_to_update[col] = str(value)
                    response = supabase.table("live_dispatches").update(data_to_update).eq("id", row_id).execute()
                    if response.data:
                        st.success(f"Row with ID {row_id} updated successfully in live_dispatches!")
                    else:
                        st.error(f"Failed to update row {row_id}: {response.status_code} - {response.status_code}")
            else:
                st.info("No changes detected in the table to save.")
            load_live_dispatches_data.clear()
            if 'df_live_dispatches_page2' in st.session_state:
                del st.session_state.df_live_dispatches_page2
            st.rerun()
        except Exception as e:
            st.error(f"An error occurred while saving changes to live_dispatches: {e}")
    st.markdown("---")
    st.header("Add New Live Dispatch Ticket")
    tech_options, site_options = load_tech_site_data()
    with st.form("new_live_dispatch_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            new_date = st.date_input("Date:", value=datetime.today(), key="live_form_new_date")
            selected_tech = st.selectbox("Tech:", options=[""] + tech_options, index=0, key="live_form_new_tech_select")
            sla_options = ["2 Hour", "4 Hour", "2 Day", "4 Day"]
            new_sla = st.selectbox("Select SLA:", sla_options, key="live_form_new_sla")        
        with col2:
            selected_site = st.selectbox("Site:", options=[""] + site_options, index=0, key="live_form_new_site_select")
            new_hours = st.number_input("Hours:", value=0.0, min_value=0.0, format="%.2f", key="live_form_new_hours")
            new_additional = st.number_input("Additional ($):", value=0.0, min_value=0.0, format="%.2f", key="form_new_additional")
        add_button = st.form_submit_button("Add New Live Ticket")
        if add_button:
            new_row_data = {
                "Date": new_date.strftime('%Y-%m-%d'),
                "Tech": selected_tech,
                "Site": selected_site,
                "SLA": new_sla,
                "Hours": new_hours,
                "Additional": new_additional}
            try:
                response = supabase.table("live_dispatches").insert([new_row_data]).execute()
                if response.data:
                    st.success("New live ticket added to Supabase successfully! Triggers should populate other fields.")
                    load_live_dispatches_data.clear()
                    if 'df_live_dispatches_page2' in st.session_state:
                        del st.session_state.df_live_dispatches_page2
                    st.rerun()
                else:
                    st.error(f"Failed to add new live ticket: {response.status_code} - {response.status_code}")
                    st.json(response.data)
            except Exception as e:
                st.error(f"An error occurred while adding new live ticket: {e}")

def PAGE_3():
    st.title("Reporting on Startup Budget")
    st.write("Startup Fee - $35,000")
    @st.cache_data(ttl="1h")
    def load_budget_data():
        try:
            response = supabase.table("badging_dispatches").select("Total").execute()
            data = response.data
            if data:
                df_budget = pd.DataFrame(data)
                if 'Total' in df_budget.columns:
                    df_budget['Total'] = pd.to_numeric(df_budget['Total'], errors='coerce').fillna(0.0)
                else:
                    st.warning("Warning: 'Total' column not found in 'badging_dispatches' table for budget calculation.")
                    df_budget['Total'] = 0.0
                return df_budget
            return pd.DataFrame(columns=['Total'])
        except Exception as e:
            st.error(f"Error loading budget data from Supabase: {e}")
            return pd.DataFrame(columns=['Total'])
    STARTUP_REPORT = load_budget_data()
    st.subheader("Budget Breakdown")
    total_budget = 35000.00
    if 'Total' in STARTUP_REPORT.columns:
        paid_funds = STARTUP_REPORT['Total'].sum()
    else:
        st.warning("Cannot calculate 'Paid Funds' as 'Total' column is missing or not numeric in loaded data.")
        paid_funds = 0.0
    unallocated_funds = total_budget - paid_funds
    if unallocated_funds < 0:
        st.warning(f"Warning: Paid Funds (${paid_funds:,.2f}) exceed Total Budget (${total_budget:,.2f}). Unallocated funds will be shown as $0.00.")
        unallocated_funds = 0.0
    labels = ['Spent', 'Unallocated Funds']
    sizes = [paid_funds, unallocated_funds]
    def autopct_format(pct, allvals):
        absolute_value = (pct / 100.) * sum(allvals)
        return f"{pct:.1f}%\n(${absolute_value:,.2f})"
    filtered_labels = [label for i, label in enumerate(labels) if sizes[i] > 0]
    filtered_sizes = [size for size in sizes if size > 0]
    if not filtered_sizes:
        st.info("No funds to display in the pie chart yet. Total column might be empty or zero.")
        if total_budget > 0:
            filtered_labels = ['Unallocated Funds']
            filtered_sizes = [total_budget]
        else:
            filtered_labels = ['No Budget Set']
            filtered_sizes = [1]
    fig1, ax1 = plt.subplots(figsize=(8, 6))
    ax1.pie(filtered_sizes, labels=filtered_labels, autopct=lambda pct: autopct_format(pct, filtered_sizes), startangle=90,
            colors=sns.color_palette("pastel"))
    ax1.axis('equal')
    ax1.set_title(f"Budget Allocation")
    st.pyplot(fig1)
    st.markdown("---")
    st.title("Reporting on Badging Process")
    st.write("Broken Down by Site")
    @st.cache_data(ttl="1h")
    def load_badging_report_data():
        try:
            response = supabase.table("names_and_sites").select("Name, Site, Badge").execute()
            data = response.data
            if data:
                df_badging_temp = pd.DataFrame(data)
                if 'Badge' in df_badging_temp.columns:
                    df_badging_temp['Badge'] = df_badging_temp['Badge'].astype(str).str.upper().str.strip()
                    df_badging_temp['Badge'] = df_badging_temp['Badge'].replace({'Y': 'YES', 'N': 'NO'})
                    df_badging_temp = df_badging_temp[df_badging_temp['Badge'].isin(['YES', 'NO'])]
                else:
                    st.error("Error: 'BADGED' column not found in the 'names_and_sites' table. Cannot process badging data.")
                    return pd.DataFrame(columns=['Site', 'Badge', 'Name'])
                if 'Site' not in df_badging_temp.columns:
                    st.error("Error: 'SITE' column not found in the 'names_and_sites' table. Cannot process badging data.")
                    return pd.DataFrame(columns=['Site', 'Badge', 'Name'])
                if 'Name' not in df_badging_temp.columns:
                    st.error("Error: 'NAME' column not found in the 'names_and_sites' table. Cannot process badging data.")
                    return pd.DataFrame(columns=['Site', 'Badge', 'Name'])
                return df_badging_temp.copy()
            return pd.DataFrame(columns=['Site', 'Badge', 'Name'])
        except Exception as e:
            st.error(f"Error loading badging report data from Supabase: {e}")
            return pd.DataFrame(columns=['Site', 'Badge', 'Name'])
    df_badging = load_badging_report_data()
    if not df_badging.empty and 'Site' in df_badging.columns and 'Badge' in df_badging.columns:
        total_techs_per_site = df_badging.groupby('Site').size().reset_index(name='Total Techs')
        badged_counts = df_badging.groupby(['Site', 'Badge']).size().unstack(fill_value=0).reset_index()
        site_summary = pd.merge(total_techs_per_site, badged_counts, on='Site', how='left')
        site_summary = site_summary.fillna(0)
        if 'YES' not in site_summary.columns:
            site_summary['YES'] = 0
        if 'NO' not in site_summary.columns:
            site_summary['NO'] = 0
        site_summary['Badged Fraction'] = site_summary.apply(
            lambda row: f"{int(row['YES'])}/{int(row['Total Techs'])}" if row['Total Techs'] > 0 else "0/0", axis=1)
        site_summary['Badged %'] = site_summary.apply(
            lambda row: round((row['YES'] / row['Total Techs'] * 100), 2) if row['Total Techs'] > 0 else 0.0, axis=1)
        site_summary['Not Badged Fraction'] = site_summary.apply(
            lambda row: f"{int(row['NO'])}/{int(row['Total Techs'])}" if row['Total Techs'] > 0 else "0/0", axis=1)
        site_summary['Not Badged %'] = site_summary.apply(
            lambda row: round((row['NO'] / row['Total Techs'] * 100), 2) if row['Total Techs'] > 0 else 0.0, axis=1)
        site_summary_display = site_summary[['Site','Badged Fraction', 'Badged %']]
        site_summary_display.columns = ['Site', 'Badged (Fraction)', 'Badged (%)']
        st.subheader("Badging Progress Summary by Site")
        st.dataframe(site_summary_display, use_container_width=True)
    else:
        st.info("No badging data available to generate summary by site.")
    st.subheader("Badging Progress Chart")
    if not df_badging.empty and 'Site' in df_badging.columns and 'Badge' in df_badging.columns:
        if 'site_summary' not in locals():
             total_techs_per_site = df_badging.groupby('Site').size().reset_index(name='Total Techs')
             badged_counts = df_badging.groupby(['Site', 'Badge']).size().unstack(fill_value=0).reset_index()
             site_summary = pd.merge(total_techs_per_site, badged_counts, on='Site', how='left')
             site_summary = site_summary.fillna(0)
             if 'YES' not in site_summary.columns: site_summary['YES'] = 0
             if 'NO' not in site_summary.columns: site_summary['NO'] = 0
        chart_data = site_summary[['Site', 'YES', 'NO']].melt(id_vars=['Site'], var_name='Status', value_name='Count')
        chart_data['Status'] = chart_data['Status'].replace({'YES': 'Badged', 'NO': 'Not Badged'})
        if not chart_data.empty:
            chart = alt.Chart(chart_data).mark_bar().encode(
                x=alt.X('Site:N', title='Site'),
                y=alt.Y('Count:Q', title='Number of Technicians'),
                color=alt.Color('Status:N', title='Badging Status', scale=alt.Scale(domain=['Badged', 'Not Badged'], range=['#4CAF50', '#FFC107'])),
                order=alt.Order('Status', sort='descending'),
                tooltip=['Site', 'Status', 'Count']).properties(
                title='Badging Progress per Site').interactive()
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Not enough data to generate the badging progress chart.")
    else:
        st.info("No badging data available to generate the badging progress chart.")
    st.subheader("Badging Statistics")
    if not df_badging.empty and 'Site' in df_badging.columns and 'Badge' in df_badging.columns:
        if 'site_summary' not in locals():
             total_techs_per_site = df_badging.groupby('Site').size().reset_index(name='Total Techs')
             badged_counts = df_badging.groupby(['Site', 'Badge']).size().unstack(fill_value=0).reset_index()
             site_summary = pd.merge(total_techs_per_site, badged_counts, on='Site', how='left')
             site_summary = site_summary.fillna(0)
             if 'YES' not in site_summary.columns: site_summary['YES'] = 0
             if 'NO' not in site_summary.columns: site_summary['NO'] = 0
        sites_over_65_percent_badged = site_summary[site_summary['Badged %'] > 65]
        num_sites_over_65_percent = len(sites_over_65_percent_badged)
        st.write(f"Number of sites with **over 65%** of technicians badged: **{num_sites_over_65_percent}**")
        if num_sites_over_65_percent > 0:
            site_names_list = sites_over_65_percent_badged['Site'].tolist()
            sites_string = ", ".join(site_names_list)
            st.write(f"Live Sites: **{sites_string}**")
        else:
            st.info("No sites currently have over 65% of their technicians badged.")
        unique_yes_count = df_badging[df_badging['Badge'] == 'YES']['Name'].nunique()
        unique_no_count = df_badging[df_badging['Badge'] == 'NO']['Name'].nunique()
        st.write(f"Technicians Badged: **{unique_yes_count}**")
        st.write(f"Pending Badge Completion/Pickup: **{unique_no_count}**")
        total_unique_names = unique_yes_count + unique_no_count
        if total_unique_names > 0:
            percent_badged = (unique_yes_count / total_unique_names) * 100
            st.write(f"Percent Badged: **{percent_badged:.1f}%**")
        else:
            st.info("No technicians found in the badging data to calculate percentages.")
    else:
        st.info("No badging data available to generate badging statistics.")


def PAGE_4():
    st.title("PNL Report")
    st.header("Live Dispatches Statistics")
    @st.cache_data(ttl=300)
    def load_live_dispatches_data():
        try:
            response = supabase.table("live_dispatches").select("*").execute()
            data = response.data
            if data:
                df_loaded = pd.DataFrame(data)
                if "SLA" not in df_loaded.columns:
                    st.error("Error: 'SLA' column not found in 'live_dispatches' table. Please check your Supabase table schema.")
                    return pd.DataFrame()
                df_loaded["SLA"] = df_loaded["SLA"].astype(str)
                if "Date" in df_loaded.columns:
                    df_loaded["Date"] = pd.to_datetime(df_loaded["Date"], errors='coerce', format='%Y-%m-%d')
                    initial_rows = len(df_loaded)
                    df_loaded.dropna(subset=['Date'], inplace=True)
                    if len(df_loaded) < initial_rows:
                        st.warning(f"Removed {initial_rows - len(df_loaded)} rows due to invalid 'Date' values.")
                else:
                    st.error("Error: 'Date' column not found in 'live_dispatches' table. Monthly analysis will not be available.")
                    return pd.DataFrame() # Return empty if Date column is critical for this page
                if not pd.api.types.is_datetime64_any_dtype(df_loaded['Date']):
                    st.error(f"Error: 'Date' column is not a datetime type after conversion. Current type: {df_loaded['Date'].dtype}. Check date format in Supabase.")
                    return pd.DataFrame() # Stop if Date is still not datetime
                financial_cols = ["Total FN Pay", "Total DXC Pay", "PNL"]
                for col in financial_cols:
                    if col in df_loaded.columns:
                        df_loaded[col] = pd.to_numeric(df_loaded[col], errors='coerce').fillna(0.0)
                    else:
                        st.warning(f"Warning: '{col}' column not found in 'live_dispatches' table. Financial calculations for this column will be zero.")
                        df_loaded[col] = 0.0
                return df_loaded
            else:
                st.info("No data received from 'live_dispatches' table.")
                return pd.DataFrame()
        except Exception as e:
            st.error(f"Error loading live dispatches data: {e}")
            return pd.DataFrame()
    df_live_dispatches = load_live_dispatches_data()
    if not df_live_dispatches.empty:
        total_rows = len(df_live_dispatches)
        st.write(f"**Total Number of Live Dispatches (excluding header):** {total_rows}")
        st.subheader("SLA Counts")
        known_slas = ['2 Hour', '4 Hour', '2 Day', '4 Day']
        sla_counts_series = df_live_dispatches['SLA'].value_counts()
        display_sla_counts = {sla: sla_counts_series.get(sla, 0) for sla in known_slas}
        other_sla_count = 0
        for sla_val in df_live_dispatches['SLA'].unique():
            if sla_val not in known_slas and pd.notna(sla_val) and sla_val.strip() != '':
                other_sla_count += sla_counts_series.get(sla_val, 0)
        display_sla_counts['Other'] = other_sla_count
        st.write(f"**2 Hour SLA:** {display_sla_counts['2 Hour']}")
        st.write(f"**4 Hour SLA:** {display_sla_counts['4 Hour']}")
        st.write(f"**2 Day SLA:** {display_sla_counts['2 Day']}")
        st.write(f"**4 Day SLA:** {display_sla_counts['4 Day']}")
        if display_sla_counts['Other'] > 0:
            st.write(f"**Other SLA Types:** {display_sla_counts['Other']}")
            other_sla_df = df_live_dispatches[~df_live_dispatches['SLA'].isin(known_slas) & df_live_dispatches['SLA'].notna() & (df_live_dispatches['SLA'].astype(str).str.strip() != '')]
            st.dataframe(other_sla_df[['SLA']])
        # --- Monthly Financial Analysis Section ---
        st.markdown("---")
        st.header("Monthly Financial Analysis")
        if "Date" in df_live_dispatches.columns and pd.api.types.is_datetime64_any_dtype(df_live_dispatches['Date']):
            df_live_dispatches['MonthYear'] = df_live_dispatches['Date'].dt.strftime('%Y-%m')
            month_year_options = sorted(df_live_dispatches['MonthYear'].unique(), reverse=True)
            if month_year_options:
                selected_month_year = st.selectbox(
                    "Select Month/Year for Report:",
                    options=month_year_options,
                    index=0)
                df_filtered_month = df_live_dispatches[df_live_dispatches['MonthYear'] == selected_month_year].copy()
                if not df_filtered_month.empty:
                    st.subheader(f"Financial Summary for {selected_month_year}")
                    total_fn_pay = df_filtered_month["Total FN Pay"].sum()
                    total_dxc_pay = df_filtered_month["Total DXC Pay"].sum()
                    total_pnl = df_filtered_month["PNL"].sum()
                    num_tickets_month = len(df_filtered_month)
                    avg_fn_pay_per_ticket = total_fn_pay / num_tickets_month if num_tickets_month > 0 else 0
                    avg_dxc_pay_per_ticket = total_dxc_pay / num_tickets_month if num_tickets_month > 0 else 0
                    avg_pnl_per_ticket = total_pnl / num_tickets_month if num_tickets_month > 0 else 0
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Field Nation Pay", f"${total_fn_pay:,.2f}")
                    with col2:
                        st.metric("Total DXC Pay", f"${total_dxc_pay:,.2f}")
                    with col3:
                        st.metric("Total PNL", f"${total_pnl:,.2f}")
                    st.markdown("---") # Separator line
                    st.subheader(f"Average Pay Per Ticket for {selected_month_year}")
                    col4, col5, col6 = st.columns(3)
                    with col4:
                        st.metric("Avg FN Pay Per Ticket", f"${avg_fn_pay_per_ticket:,.2f}")
                    with col5:
                        st.metric("Avg DXC Pay Per Ticket", f"${avg_dxc_pay_per_ticket:,.2f}")
                    with col6:
                        st.metric("Avg PNL Per Ticket", f"${avg_pnl_per_ticket:,.2f}")
                    st.markdown("---") # Separator line
                    st.subheader(f"Ticket Breakdown for {selected_month_year}")
                    col_breakdown1, col_breakdown2 = st.columns(2)
                    with col_breakdown1:
                        st.write("#### By SLA Category")
                        # Get SLA counts for the filtered month
                        sla_breakdown_month = df_filtered_month['SLA'].value_counts().sort_index()
                        if not sla_breakdown_month.empty:
                            st.dataframe(sla_breakdown_month.reset_index().rename(columns={'index': 'SLA Category', 'SLA': 'Ticket Count'}), hide_index=True)
                        else:
                            st.info("No SLA breakdown data for this month.")
                    with col_breakdown2:
                        st.write("#### By Site")
                        # Get Site counts for the filtered month
                        # Ensure 'Site' column is present and valid before counting
                        if "Site" in df_filtered_month.columns:
                            site_breakdown_month = df_filtered_month['Site'].value_counts().sort_index()
                            if not site_breakdown_month.empty:
                                st.dataframe(site_breakdown_month.reset_index().rename(columns={'index': 'Site', 'Site': 'Ticket Count'}), hide_index=True)
                            else:
                                st.info("No Site breakdown data for this month.")
                        else:
                            st.info("Site column not available for breakdown.")
                else:
                    st.info(f"No data available for {selected_month_year}.")
            else:
                st.info("No valid month/year data found for financial analysis.")
        else:
            st.info("Date column is missing or not correctly formatted as datetime, unable to perform monthly financial analysis.")
    else:
        st.info("No data found in 'live_dispatches' table or an error occurred during loading.")





# --- Main Application Logic ---
st.sidebar.title("Navigation")
page_selection = st.sidebar.radio(
    "Go to",
    ("Home", "Badging Tickets", "Live Dispatches", "Reporting Page", "PNL Report"))
if page_selection == "Home":
    home_page()
elif page_selection == "Badging Tickets":
    PAGE_1()
elif page_selection == "Live Dispatches":
    PAGE_2()
elif page_selection == "Reporting Page":
    PAGE_3()
elif page_selection == "PNL Report":
    PAGE_4()
