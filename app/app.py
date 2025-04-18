import streamlit as st
import streamlit.components.v1 as components
import base64
import leafmap.maplibregl as leafmap
import altair as alt
import ibis
from ibis import _
import ibis.selectors as s
import os
import pandas as pd 
import geopandas as gpd
from shapely import wkb  
import sqlalchemy
import pathlib
from typing import Optional
from functools import reduce

from variables import *
from utils import *

## Create the table from remote parquet only if it doesn't already exist on disk
con = ibis.duckdb.connect("duck.db", extensions=["spatial"])
current_tables = con.list_tables()

if "mydata" not in set(current_tables):
    tbl = con.read_parquet(ca_parquet)
    con.create_table("mydata", tbl)

ca = con.table("mydata")

# session state for syncing app 
for key in [
    'richness', 'rsr', 'irrecoverable_carbon', 'manageable_carbon',
    'fire', 'rxburn', 'disadvantaged_communities',
    'svi']:
    if key not in st.session_state:
        st.session_state[key] = False

for col,val in style_options.items():
    for name in val['stops']:
        key = val['property']+str(name[0])
        if key not in st.session_state:
            st.session_state[key] = default_boxes.get(name[0], True)


st.set_page_config(layout="wide", page_title="CA Protected Areas Explorer", page_icon=":globe:")

#customizing style with CSS 
st.markdown(
    """
    <style>
        /* Customizing font size for radio text */
        div[class*="stRadio"] > label > div[data-testid="stMarkdownContainer"] > p {
            font-size: 18px !important;
        }
        /* Reduce margin below the header */
        h2 {
            margin-top: 0rem !important; 
            margin-bottom: 0rem !important; /* Reduce space below headers */
        }
        /* Customizing font size for medium-font class */
        .medium-font {
            font-size: 18px !important; 
            margin-top: 0rem !important;
            margin-bottom: 0.25rem !important; /* Reduce space below */
        }
        .medium-font-sidebar {
            font-size: 17px !important;
            margin-bottom: 0.75rem !important; /* Reduce space below */
        }
        /* Customizing layout and divider */
        hr {
            margin-top: 0rem !important;  /* Adjust to reduce top margin */
            margin-bottom: 0.5rem !important; /* Adjust to reduce bottom margin */
        }
        .stAppHeader {
            background-color: rgba(255, 255, 255, 0.0);  /* Transparent background */
            visibility: visible;  /* Ensure the header is visible */
        }
        .block-container {
            padding-top: 0.5rem;
            padding-bottom: 2rem;
            padding-left: 5rem;
            padding-right: 5rem;
        }
        /* Reduce whitespace for the overall expander container */
        .st-expander {
            margin-top: 0rem;  /* Space above the expander */
            margin-bottom: 0rem; /* Space below the expander */
        }
        /* Adjust padding for the content inside the expander */
        .st-expander-content {
            padding: 0rem 0rem;  /* Reduce padding inside */
        }
        /* Optional: Adjust the expander header if needed */
        .st-expander-header {
            margin-top: 0rem;
            margin-bottom: 0rem;
        }
        .spacer { margin-bottom: 30px; } /* padding in sidebar */
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <style>
        /* Remove or reduce whitespace at the top of the sidebar */
        [data-testid="stSidebar"] > div:first-child {
            padding-top: 0rem !important; 
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("<h2>CA 30x30 Planning & Assessment Prototype</h2>", unsafe_allow_html=True)

st.markdown('<p class="medium-font"> In October 2020, Governor Newsom issued <a href="https://www.gov.ca.gov/wp-content/uploads/2020/10/10.07.2020-EO-N-82-20-.pdf" target="_blank">Executive Order N-82-20</a>, which establishes a state goal of conserving 30% of California’s lands and coastal waters by 2030 – known as <a href="https://www.californianature.ca.gov/" target="_blank">CA 30x30</a>. </p>',
unsafe_allow_html=True)

st.markdown('<p class = "medium-font"> This is an interactive cloud-native geospatial tool for exploring and visualizing California\'s protected lands. </p>', unsafe_allow_html = True)

st.divider()

           
m = leafmap.Map(style="positron")
#############


chatbot_container = st.container()
with chatbot_container:
    llm_left_col, llm_right_col = st.columns([5,1], vertical_alignment = "bottom")
    with llm_left_col:

        with st.popover("💬 Example Queries"):
            '''
            Mapping queries:        
            - Show me areas open to the public that are in the top 10% of species richness.
            - Show me all GAP 1 and 2 lands managed by The Nature Conservancy.
            - Show me state land smaller than 1000 acres, with a social vulnerability index in the 90th percentile.
            - Show me GAP 3 and 4 lands managed by BLM in the top 5% of range-size rarity.
            - Show me Joshua Tree National Park.
            - Show me all protected lands that have experienced forest fire over at least 50% of their area.
            - Show me the biggest protected area in California. 
            - Show me all land managed by the United States Forest Service. 
            '''
            
            '''
            Exploratory data queries:
            - What is a GAP code?
            - What percentage of 30x30 conserved land has been impacted by wildfire?
            - What is the total acreage of areas designated as easements?
            - Who manages the land with the highest amount of irrecoverable carbon and highest social vulnerability index? 
            '''
            
            st.info('If the map appears blank, queried data may be too small to see at the default zoom level. Check the table below the map, as query results will also be displayed there.', icon="ℹ️")


    with llm_right_col:
        llm_choice = st.selectbox("Select LLM:", llm_options, key = "llm", help = "Select which model to use.")   
        llm = llm_options[llm_choice]
        
##### Chatbot stuff       
from pydantic import BaseModel, Field
class SQLResponse(BaseModel):
    """Defines the structure for SQL response."""
    sql_query: str = Field(description="The SQL query generated by the assistant.")
    explanation: str = Field(description="A detailed explanation of how the SQL query answers the input question.")

with open('app/system_prompt.txt', 'r') as file:
    template = file.read()

from langchain_openai import ChatOpenAI

managers = ca.sql("SELECT DISTINCT manager FROM mydata;").execute()
names = ca.sql("SELECT name FROM mydata GROUP BY name HAVING SUM(acres) >10000;").execute()
ecoregions = ca.sql("SELECT DISTINCT ecoregion FROM mydata;").execute()

from langchain_core.prompts import ChatPromptTemplate
prompt = ChatPromptTemplate.from_messages([
    ("system", template),
    ("human", "{input}")
]).partial(dialect="duckdb", table_info = ca.schema(), managers = managers, names = names, ecoregions = ecoregions)

structured_llm = llm.with_structured_output(SQLResponse)
few_shot_structured_llm = prompt | structured_llm

chatbot_toggles = {key: False for key in [
    'richness', 'rsr', 'irrecoverable_carbon', 'manageable_carbon',
    'fire', 'rxburn', 'disadvantaged_communities',
    'svi', 
]}

def run_sql(query,color_choice):
    """
    Filter data based on an LLM-generated SQL query and return matching IDs.

    Args:
        query (str): The natural language query to filter the data.
        color_choice (str): The column used for plotting.
    """
    output = few_shot_structured_llm.invoke(query)
    sql_query = output.sql_query
    explanation =output.explanation
    if not sql_query: # if the chatbot can't generate a SQL query.
        st.success(explanation)
        return pd.DataFrame({'id' : []})
        
    result = ca.sql(sql_query).execute()
    if result.empty :
        explanation = "This query did not return any results. Please try again with a different query."
        st.warning(explanation, icon="⚠️")
        st.caption("SQL Query:")
        st.code(sql_query,language = "sql") 
        if 'geom' in result.columns:
            return result.drop('geom',axis = 1)
        else: 
            return result
    
    elif ("id" and "geom" in result.columns): 
        style = get_pmtiles_style_llm(style_options[color_choice], result["id"].tolist())
        legend, position, bg_color, fontsize = get_legend(style_options,color_choice)

        m.add_legend(legend_dict = legend, position = position, bg_color = bg_color, fontsize = fontsize)
        m.add_pmtiles(ca_pmtiles, style=style, opacity=alpha, tooltip=True, fit_bounds=True)
        m.fit_bounds(result.total_bounds.tolist())    
        result = result.drop('geom',axis = 1) #printing to streamlit so I need to drop geom
    else:   
        st.write(result)  # if we aren't mapping, just print out the data  

    with st.popover("Explanation"):
        st.write(explanation)
        st.caption("SQL Query:")
        st.code(sql_query,language = "sql") 
        
    return result




#############

filters = {}

with st.sidebar:
    with st.popover("ℹ️ Help"):
        '''
        - ❌ Safari/iOS not yet supported. For Safari/iOS users, try [this version](https://huggingface.co/spaces/boettiger-lab/ca-30x30-folium) with similar functionality. 
        - 📊 Use this sidebar to color-code the map by different attributes **(Group by)**, toggle on data layers and view summary charts **(Data Layers)**, or filter data **(Filters)**.
        - 💬 For a more tailored experience, query our dataset of protected areas and their precomputed mean values for each of the displayed layers, using the experimental chatbot. The language model tries to answer natural language questions by drawing only from curated datasets (listed below).
        '''

    
    st.divider()
    color_choice = st.radio("Group by:", style_options, key = "color", help = "Select a category to change map colors and chart groupings.")   
    colorby_vals = get_color_vals(style_options, color_choice) #get options for selected color_by column 
    alpha = 0.8
    st.divider()


##### Chatbot 
with chatbot_container:
    with llm_left_col:
        example_query = "👋 Input query here"
        prompt = st.chat_input(example_query, key="chain", max_chars=300)


with st.container():
    if prompt: 
        st.chat_message("user").write(prompt)
        try:
            with st.chat_message("assistant"):
                with st.spinner("Invoking query..."):

                    out = run_sql(prompt,color_choice)
                    if ("id" in out.columns) and (not out.empty):
                        ids = out['id'].tolist()
                        cols = out.columns.tolist()
                        chatbot_toggles = {
                                key: (True if key in cols else value) 
                                for key, value in chatbot_toggles.items()
                            }
                        for key, value in chatbot_toggles.items():
                            st.session_state[key] = value  # Update session state
                    else:
                        ids = []
        except Exception as e:
            error_message = f"ERROR: An unexpected error has occured with the following query:\n\n*{prompt}*\n\n which raised the following error:\n\n{type(e)}: {e}\n"
            st.warning("Please try again with a different query", icon="⚠️")
            st.write(error_message)
            st.stop()


#### Data layers 
with st.sidebar:  
    st.markdown('<p class = "medium-font-sidebar"> Data Layers:</p>', help = "Select data layers to visualize on the map. Summary charts will update based on the displayed layers.", unsafe_allow_html= True)
    # Biodiversity Section 
    with st.expander("🦜 Biodiversity"):
        a_bio = st.slider("transparency", 0.0, 1.0, 0.1, key = "biodiversity")
        show_richness = st.toggle("Species Richness", key = "richness", value=chatbot_toggles['richness'])
        show_rsr = st.toggle("Range-Size Rarity", key = "rsr", value=chatbot_toggles['rsr'])
        
        if show_richness:
            m.add_tile_layer(url_sr, name="MOBI Species Richness",opacity=a_bio)
        if show_rsr:           
            m.add_tile_layer(url_rsr, name="MOBI Range-Size Rarity", opacity=a_bio)

    #Carbon Section
    with st.expander("⛅ Carbon & Climate"):
        a_climate = st.slider("transparency", 0.0, 1.0, 0.15, key = "climate")
        show_irrecoverable_carbon = st.toggle("Irrecoverable Carbon", key = "irrecoverable_carbon", value=chatbot_toggles['irrecoverable_carbon'])
        show_manageable_carbon = st.toggle("Manageable Carbon", key = "manageable_carbon", value=chatbot_toggles['manageable_carbon'])
        
        if show_irrecoverable_carbon:
            m.add_cog_layer(url_irr_carbon, palette="reds", name="Irrecoverable Carbon", opacity = a_climate, fit_bounds=False)
        
        if show_manageable_carbon:
           m.add_cog_layer(url_man_carbon, palette="purples", name="Manageable Carbon", opacity = a_climate, fit_bounds=False)


    # People Section 
    with st.expander("👤 People"):
        a_people = st.slider("transparency", 0.0, 1.0, 0.1, key = "SVI")
        show_justice40 = st.toggle("Disadvantaged Communities (Justice40)", key = "disadvantaged_communities", value=chatbot_toggles['disadvantaged_communities'])
        show_sv = st.toggle("Social Vulnerability Index (SVI)", key = "svi", value=chatbot_toggles['svi'])
        
        if show_justice40:
            m.add_pmtiles(url_justice40, style=justice40_style, name="Justice40", opacity=a_people, tooltip=False, fit_bounds = False)
            
        if show_sv:
            m.add_pmtiles(url_svi, style = svi_style, opacity=a_people, tooltip=False, fit_bounds = False)
        
    # Fire Section
    with st.expander("🔥 Fire"):
        a_fire = st.slider("transparency", 0.0, 1.0, 0.15, key = "calfire")
        show_fire = st.toggle("Fires (2013-2023)", key = "fire", value=chatbot_toggles['fire'])

        show_rxburn = st.toggle("Prescribed Burns (2013-2023)", key = "rxburn", value=chatbot_toggles['rxburn'])


        if show_fire:
            m.add_pmtiles(url_calfire, style=fire_style, name="CALFIRE Fire Polygons (2013-2023)", opacity=a_fire, tooltip=False, fit_bounds = False)

        if show_rxburn:
            m.add_pmtiles(url_rxburn, style=rx_style, name="CAL FIRE Prescribed Burns (2013-2023)", opacity=a_fire, tooltip=False, fit_bounds = False)
                    

    st.divider()
    st.markdown('<p class = "medium-font-sidebar"> Filters:</p>', help = "Apply filters to adjust what data is shown on the map.", unsafe_allow_html= True)

    for label in style_options: # get selected filters (based on the buttons selected)
        with st.expander(label):  
            if label in ["GAP Code","30x30 Status"]: # gap code 1 and 2 are on by default
                opts = get_buttons(style_options, label, default_boxes)
            else: # other buttons are not on by default.
                opts = get_buttons(style_options, label) 
            filters.update(opts)
            
        selected = {k: v for k, v in filters.items() if v}
        if selected: 
            filter_cols = list(selected.keys())
            filter_vals = list(selected.values())
        else: 
            filter_cols = []
            filter_vals = []

    st.divider()
    
    # adding github logo 
    st.markdown(f"<div class='spacer'>{github_html}</div>", unsafe_allow_html=True)
    
    # st.markdown("""
    # <p class='medium-font-sidebar'> 
    # :left_speech_bubble: <a href='https://github.com/boettiger-lab/ca-30x30/issues' target='_blank'>Report an issue</a>
    # </p> 
    # """, unsafe_allow_html=True)

    st.markdown(":left_speech_bubble: [Get in touch or report an issue](https://github.com/boettiger-lab/ca-30x30/issues)")





# Display CA 30x30 Data
if 'out' not in locals():
    style = get_pmtiles_style(style_options[color_choice], alpha, filter_cols, filter_vals)
    legend, position, bg_color, fontsize = get_legend(style_options, color_choice)
    m.add_legend(legend_dict = legend, position = position, bg_color = bg_color, fontsize = fontsize)
    m.add_pmtiles(ca_pmtiles, style=style, name="CA", opacity=alpha, tooltip=True, fit_bounds=True)
    
column = select_column[color_choice]

select_colors = {
    "30x30 Status": status["stops"],
    "GAP Code": gap["stops"],
    "Year": year["stops"],
    "Ecoregion": ecoregion["stops"],
    "Manager Type": manager["stops"],
    "Easement": easement["stops"],
    "Access Type": access["stops"],
}

colors = (
    ibis
    .memtable(select_colors[color_choice], columns=[column, "color"])
    .to_pandas()
)


# get summary tables used for charts + printed table 
# df - charts; df_tab - printed table (omits colors) 
if 'out' not in locals():
    df, df_tab, df_percent, df_bar_30x30 = get_summary_table(ca, column, select_colors, color_choice, filter_cols, filter_vals,colorby_vals)
    total_percent = (100*df_percent.percent_CA.sum()).round(2)

else:
    df = get_summary_table_sql(ca, column, colors, ids)
    total_percent = (100*df.percent_CA.sum()).round(2)


# charts displayed based on color_by variable
richness_chart = bar_chart(df, column, 'mean_richness', "Species Richness (2022)")
rsr_chart = bar_chart(df, column, 'mean_rsr', "Range-Size Rarity (2022)")
irr_carbon_chart = bar_chart(df, column, 'mean_irrecoverable_carbon', "Irrecoverable Carbon (2018)")
man_carbon_chart = bar_chart(df, column, 'mean_manageable_carbon', "Manageable Carbon (2018)")
fire_10_chart = bar_chart(df, column, 'mean_fire', "Fires (2013-2023)")
rx_10_chart = bar_chart(df, column, 'mean_rxburn',"Prescribed Burns (2013-2023)")
justice40_chart = bar_chart(df, column, 'mean_disadvantaged', "Disadvantaged Communities (2021)")
svi_chart = bar_chart(df, column, 'mean_svi', "Social Vulnerability Index (2022)")

main = st.container()

with main:
    map_col, stats_col = st.columns([2,1])

    with map_col:
        m.to_streamlit(height=650)
        with st.expander("🔍 View/download data"):
            if 'out' not in locals():
                st.dataframe(df_tab, use_container_width = True)  
            else:
                st.dataframe(out, use_container_width = True)

    with stats_col:
        with st.container():
            
            st.markdown(f"{total_percent}% CA Protected", help = "Total percentage of 30x30 conserved lands, updates based on displayed data")
            st.altair_chart(area_chart(df, column), use_container_width=True)
            
            if 'df_bar_30x30' in locals(): #if we use chatbot, we won't have these graphs.
                if column not in ["status", "gap_code"]:
                    st.altair_chart(stacked_bar(df_bar_30x30, column,'percent_group','status', color_choice + ' by 30x30 Status',colors), use_container_width=True)

            if show_richness:
                st.altair_chart(richness_chart, use_container_width=True)

            if show_rsr:
                st.altair_chart(rsr_chart, use_container_width=True)

            if show_irrecoverable_carbon:
                st.altair_chart(irr_carbon_chart, use_container_width=True)

            if show_manageable_carbon:
                st.altair_chart(man_carbon_chart, use_container_width=True)

            if show_justice40:
                st.altair_chart(justice40_chart, use_container_width=True)
                
            if show_sv:
                st.altair_chart(svi_chart, use_container_width=True)

            if show_fire:
                st.altair_chart(fire_10_chart, use_container_width=True)
                
            if show_rxburn:
                st.altair_chart(rx_10_chart, use_container_width=True)


st.caption("***The label 'established' is inferred from the California Protected Areas Database, which may introduce artifacts. For details on our methodology, please refer to our <a href='https://github.com/boettiger-lab/ca-30x30' target='_blank'>our source code</a>.", unsafe_allow_html=True)

            
st.caption("***Under California’s 30x30 framework, only GAP codes 1 and 2 are counted toward the conservation goal.") 

st.divider()

with open('app/footer.md', 'r') as file:
    footer = file.read()
st.markdown(footer)


