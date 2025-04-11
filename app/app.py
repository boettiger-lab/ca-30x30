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
    "ACE_amphibian", "ACE_reptile", "ACE_bird",
    "ACE_mammal", "ACE_rare_amphibian", "ACE_rare_reptile",
    "ACE_rare_bird", "ACE_rare_mammal", "ACE_end_amphibian",
    "ACE_end_reptile", "ACE_end_bird", "ACE_end_mammal",
    "plant", "end_plant", "farmlands", "grazing",
    "DAC", "low-income", "fire"]:
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
with st.popover("💬 Example Queries"):
    '''
    Mapping queries:        
    - Show me all GAP 1 and 2 lands managed by The Nature Conservancy.
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
    - Who manages the land with the highest percentage of wetlands?
    '''
    
    st.info('If the map appears blank, queried data may be too small to see at the default zoom level. Check the table below the map, as query results will also be displayed there.', icon="ℹ️")


chatbot_container = st.container()
with chatbot_container:
    llm_choice_col, llm_input_col = st.columns([1,8])

    with llm_choice_col:
        with st.popover("LLM"):
            llm_options = ['Llama-3.3-70B-Instruct-AWQ']
            llm_choice = st.radio("LLM:", llm_options, key = "llm", help = "Select which model to use.")   


##### Chatbot stuff 


from pydantic import BaseModel, Field
class SQLResponse(BaseModel):
    """Defines the structure for SQL response."""
    sql_query: str = Field(description="The SQL query generated by the assistant.")
    explanation: str = Field(description="A detailed explanation of how the SQL query answers the input question.")

with open('app/system_prompt.txt', 'r') as file:
    template = file.read()

from langchain_openai import ChatOpenAI

#llm = ChatOpenAI(model = "kosbu/Llama-3.3-70B-Instruct-AWQ", api_key = st.secrets['CIRRUS_LLM_API_KEY'], base_url = "https://llm.cirrus.carlboettiger.info/v1/",  temperature=0)
# llm = ChatOpenAI(model="gpt-4", temperature=0)
# llm = ChatOpenAI(model = "llama3", api_key=st.secrets['NRP_API_KEY'], base_url = "https://llm.nrp-nautilus.io/",  temperature=0)
if llm_choice == 'Llama-3.3-70B-Instruct-AWQ':
    llm = ChatOpenAI(model = "groq-tools", api_key=st.secrets['NRP_API_KEY'], base_url = "https://llm.nrp-nautilus.io/",  temperature=0)

# llm = ChatOpenAI(model = "llama3-sdsc", api_key=st.secrets['NRP_API_KEY'], base_url = "https://llm.nrp-nautilus.io/",  temperature=0)

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
    "ACE_amphibian", "ACE_reptile", "ACE_bird",
    "ACE_mammal", "ACE_rare_amphibian", "ACE_rare_reptile",
    "ACE_rare_bird", "ACE_rare_mammal", "ACE_end_amphibian",
    "ACE_end_reptile", "ACE_end_bird", "ACE_end_mammal",
    "plant", "end_plant", "farmlands", "grazing",
    "DAC", "low-income", "fire"
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
        - ❌ Safari/iOS not yet supported.  
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
    with llm_input_col:
    
       
    
        example_query = "👋 Input query here"
        if prompt := st.chat_input(example_query, key="chain", max_chars = 300):
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
    with st.expander("🐸 Amphibian"):
        a_amph = st.slider("transparency", 0.0, 1.0, 0.1, key = "a_amph")
        show_ACE_amph = st.toggle("Amphibian Richness", key = "ACE_amphibian")
        show_ACE_rare_amph = st.toggle("Rare Amphibian Richness", key = "ACE_rare_amphibian")
        show_ACE_end_amph = st.toggle("Endemic Amphibian Richness", key = "ACE_end_amphibian")

        if show_ACE_amph:       
            m.add_pmtiles(url_ACE_amph_richness, name = "Amphibian Richness", attribution = "CDFW (2025)", 
                          style = get_pmtiles_layer('ACE_amphibian_richness',url_ACE_amph_richness), opacity = a_amph)

        if show_ACE_rare_amph:       
            m.add_pmtiles(url_ACE_rare_amph_richness, name = "Amphibian Richness", attribution = "CDFW (2025)", 
                          style = get_pmtiles_layer('ACE_amphibian_richness',url_ACE_rare_amph_richness), opacity = a_amph)

        if show_ACE_end_amph:       
            m.add_pmtiles(url_ACE_end_amph_richness, name = "Endemic Amphibian Richness", attribution = "CDFW (2025)", 
                          style = get_pmtiles_layer('ACE_amphibian_richness',url_ACE_end_amph_richness), opacity = a_amph)

    with st.expander("🐍 Reptile"):
        a_rept = st.slider("transparency", 0.0, 1.0, 0.1, key = "a_rept")            
        show_ACE_reptile = st.toggle("Reptile Richness", key = "ACE_reptile")
        show_ACE_rare_reptile = st.toggle("Rare Reptile Richness", key = "ACE_rare_reptile")
        show_ACE_end_reptile = st.toggle("Endemic Reptile Richness", key = "ACE_end_reptile")

        if show_ACE_reptile:       
            m.add_pmtiles(url_ACE_reptile_richness, name = "Reptile Richness", attribution = "CDFW (2025)", 
                          style = get_pmtiles_layer('ACE_reptile_richness',url_ACE_reptile_richness), opacity = a_rept)

        if show_ACE_rare_reptile:       
            m.add_pmtiles(url_ACE_rare_reptile_richness, name = "Rare Reptile Richness", attribution = "CDFW (2025)", 
                          style = get_pmtiles_layer('ACE_reptile_richness',url_ACE_rare_reptile_richness), opacity = a_rept)

        if show_ACE_end_reptile:       
            m.add_pmtiles(url_ACE_end_reptile_richness, name = "Endemic Reptile Richness", attribution = "CDFW (2025)", 
                          style = get_pmtiles_layer('ACE_reptile_richness',url_ACE_end_reptile_richness), opacity = a_rept)

        
    # # Bird Section 
    with st.expander("🦜 Bird"):
        a_bird = st.slider("transparency", 0.0, 1.0, 0.1, key = "a_bird")
        show_ACE_bird = st.toggle("Bird Richness", key = "ACE_bird")
        show_ACE_rare_bird = st.toggle("Rare Bird Richness", key = "ACE_rare_bird")
        show_ACE_end_bird = st.toggle("ACE Endemic Bird Richness", key = "ACE_end_bird")
        

        if show_ACE_bird:       
            m.add_pmtiles(url_ACE_bird_richness, name = "Bird Richness", attribution = "CDFW (2025)",  
                          style = get_pmtiles_layer('ACE_bird_richness',url_ACE_bird_richness), opacity = a_bird)

        if show_ACE_rare_bird:       
            m.add_pmtiles(url_ACE_rare_bird_richness, name = "Rare Bird Richness", attribution = "CDFW (2025)",  
                          style = get_pmtiles_layer('ACE_rare_bird_richness',url_ACE_rare_bird_richness), opacity = a_bird)

        if show_ACE_end_bird:       
            m.add_pmtiles(url_ACE_end_bird_richness, name = "Endemic Bird Richness", attribution = "CDFW (2025)",  
                          style = get_pmtiles_layer('ACE_bird_richness',url_ACE_end_bird_richness), opacity = a_bird)
            
            
            # # Mammal Section 
    with st.expander("🦌 Mammal"):
        a_mammal = st.slider("transparency", 0.0, 1.0, 0.1, key = "a_mammal")

        show_ACE_mammal = st.toggle("Mammal Richness", key = "ACE_mammal")
        show_ACE_rare_mammal = st.toggle("Rare Mammal Richness", key = "ACE_rare_mammal")
        show_ACE_end_mammal = st.toggle("Endemic Mammal Richness", key = "ACE_end_mammal")


        if show_ACE_mammal:       
            m.add_pmtiles(url_ACE_mammal_richness, name = "Mammal Richness", attribution = "CDFW (2025)", 
                          style = get_pmtiles_layer('ACE_mammal_richness',url_ACE_mammal_richness), opacity = a_mammal)
        if show_ACE_rare_mammal:       
            m.add_pmtiles(url_ACE_rare_mammal_richness, name = "Rare Mammal Richness", attribution = "CDFW (2025)", 
                          style = get_pmtiles_layer('ACE_mammal_richness',url_ACE_rare_mammal_richness), opacity = a_mammal)

        if show_ACE_end_mammal:       
            m.add_pmtiles(url_ACE_end_mammal_richness, name = "Endemic Mammal Richness", attribution = "CDFW (2025)", 
                          style = get_pmtiles_layer('ACE_mammal_richness',url_ACE_end_mammal_richness), opacity = a_mammal)

        
            # # Plants Section 
    with st.expander("🌿 Plant"):
        a_plant = st.slider("transparency", 0.0, 1.0, 0.1, key = "a_plant")

        show_plant = st.toggle("Plant Richness", key = "plant")
        show_end_plant = st.toggle("Rarity-Weighted Endemic Plant Richness", key = "end_plant")
        
        if show_plant:       
            m.add_cog_layer(url_plant_richness, name = "Plant Richness", attribution =  "Kling et al. (2018)", opacity = a_plant)
        if show_end_plant:       
            m.add_cog_layer(url_endemic_plant_richness, name = "Rarity-Weighted Endemic Plant Richness", attribution = "Kling et al. (2018)", opacity = a_plant)

    ## Connectivity Section
    # with st.expander("🔗 Connectivity"):
    #     a_connect = st.slider("transparency", 0.0, 1.0, 0.1, key = "connectivity")
    #     show_resilient = st.toggle("Resilient Connected Network", key = "resilient")
    #     if show_resilient:       
    #         m.add_cog_layer(url_resilient_conn_network, name = "Resilient Connected Network", attribution = "Anderson et al. (2023)", opacity = a_connect)
    

    # Freshwater Section
    with st.expander("💧 Freshwater Resources"):
        a_freshwater= st.slider("transparency", 0.0, 1.0, 0.1, key = "freshwater")
        show_wetlands = st.toggle("Wetlands", key = "wetlands")
        
        if show_wetlands:       
            m.add_pmtiles(url_wetlands, name = "Wetlands", attribution = "National Wetland Inventory, US Fish and Wildlife Service (2019)", style = get_pmtiles_layer('CA_wetlands',url_wetlands), opacity = a_freshwater)

    # Agriculture Section
    with st.expander("🚜 Agriculture"):
        a_ag= st.slider("transparency", 0.0, 1.0, 0.1, key = "agriculture")
        show_farm = st.toggle("Farmlands", key = "farmlands")
        show_grazing = st.toggle("Grazing lands", key = "grazing")

        if show_farm:       
            m.add_pmtiles(url_farmland, name = "Farmlands", attribution = "DOC FMMP (2018)", 
                          style = get_pmtiles_layer('Farmland_2018',url_farmland), opacity = a_ag)
        if show_grazing:       
            m.add_pmtiles(url_grazing, name = "Grazing Lands", attribution = "DOC FMMP (2018)",
                          style = get_pmtiles_layer('Grazing_land_2018',url_grazing), opacity = a_ag)

    # People Section 
    with st.expander("👤 People"):
        a_people = st.slider("transparency", 0.0, 1.0, 0.1, key = "SVI")
        show_DAC = st.toggle("Disadvantaged Communities", key = "DAC")
        show_low_income = st.toggle("Low-Income Communities", key = "low-income")

        if show_DAC:
            m.add_pmtiles(url_DAC, name = "Disadvantaged Communities", attribution = "CalEnviroScreen (2022)",
                          style = get_pmtiles_layer('DAC_2022',url_DAC), opacity = a_people)
        if show_low_income:
            m.add_pmtiles(url_low_income, name = "Low-Income Communities", attribution = "CalEnviroScreen (2022)",
                          style = get_pmtiles_layer('low_income_CalEnviroScreen4',url_low_income), opacity = a_people)

    # Climate Risk Section
    with st.expander("🔥 Climate Risks"):
        a_fire = st.slider("transparency", 0.0, 1.0, 0.15, key = "calfire")
        show_fire = st.toggle("Fires (2013-2023)", key = "fire", value=chatbot_toggles['fire'])
        if show_fire:
            m.add_pmtiles(url_fire, name="Historic Fire Perimeters", attribution = "CAL FIRE (2023)",
                          style=get_pmtiles_layer('calfire_2023',url_fire),  opacity=a_fire, tooltip=False,
                          fit_bounds = True)


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
    st.markdown(":left_speech_bubble: [Get in touch or report an issue](https://github.com/boettiger-lab/CBN-taskforce/issues)")





# Display CA 30x30 Data
if 'out' not in locals():
    style = get_pmtiles_style(style_options[color_choice], alpha, filter_cols, filter_vals)
    legend, position, bg_color, fontsize = get_legend(style_options, color_choice)
    m.add_legend(legend_dict = legend, position = position, bg_color = bg_color, fontsize = fontsize)
    m.add_pmtiles(ca_pmtiles, style=style, name="CA", tooltip=True, fit_bounds=True)
    
column = select_column[color_choice]

select_colors = {
    "30x30 Status": status["stops"],
    "GAP Code": gap["stops"],
    # "Year": year["stops"],
    "Ecoregion": ecoregion["stops"],
    "Climate Zone": climate_zone["stops"],
    "Habitat Type": habitat_type["stops"],
    "Manager Type": manager["stops"],
    "Easement": easement["stops"],
    "Access Type": access["stops"],
    "Resilient & Connected Network": networks["stops"],

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
amph_chart = bar_chart(df, column, 'percent_amph_richness', "Amphibian Richness")
reptile_chart = bar_chart(df, column, 'percent_reptile_richness', "Reptile Richness")
bird_chart = bar_chart(df, column, 'percent_bird_richness', "Bird Richness")
mammal_chart = bar_chart(df, column, 'percent_mammal_richness', "Mammal Richness")
rare_amph_chart = bar_chart(df, column, 'percent_rare_amph_richness', "Rare Amphibian Richness")
rare_reptile_chart = bar_chart(df, column, 'percent_rare_reptile_richness', "Rare Reptile Richness")
rare_bird_chart = bar_chart(df, column, 'percent_rare_bird_richness', "Rare Bird Richness")
rare_mammal_chart = bar_chart(df, column, 'percent_rare_mammal_richness', "Rare Mammal Richness")
end_amph_chart = bar_chart(df, column, 'percent_end_amph_richness', "Endemic Amphibian Richness")
end_reptile_chart = bar_chart(df, column, 'percent_end_reptile_richness', "Endemic Reptile Richness")
end_bird_chart = bar_chart(df, column, 'percent_end_bird_richness', "Endemic Bird Richness")
end_mammal_chart = bar_chart(df, column, 'percent_end_mammal_richness', "Endemic Mammal Richness")
plant_chart = bar_chart(df, column, 'percent_plant_richness', "Plant Richness")
rarity_plant_chart = bar_chart(df, column, 'percent_rarityweight_endemic_plant_richness', "Rarity-Weighted\nEndemic Plant Richness")
wetlands_chart = bar_chart(df, column, 'percent_wetlands', "Wetlands")
farmland_chart = bar_chart(df, column, 'percent_farmland', "Farmland")
grazing_chart = bar_chart(df, column, 'percent_grazing', "Lands Suitable for Grazing")
DAC_chart = bar_chart(df, column, 'percent_disadvantaged', "Disadvantaged Communities")
low_income_chart = bar_chart(df, column, 'percent_low_income', "Low-Income Communities")
fire_chart = bar_chart(df, column, 'percent_fire', "Historical Fire Perimeters")



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


            if show_ACE_amph:
                st.altair_chart(amph_chart, use_container_width=True)
                
            if show_ACE_reptile:
                st.altair_chart(reptile_chart, use_container_width=True)            

            if show_ACE_bird:
                st.altair_chart(bird_chart, use_container_width=True)
                
            if show_ACE_mammal:
                st.altair_chart(mammal_chart, use_container_width=True) 

            if show_ACE_rare_amph:
                st.altair_chart(rare_amph_chart, use_container_width=True)
                
            if show_ACE_rare_reptile:
                st.altair_chart(rare_reptile_chart, use_container_width=True)            

            if show_ACE_rare_bird:
                st.altair_chart(rare_bird_chart, use_container_width=True)
                
            if show_ACE_rare_mammal:
                st.altair_chart(rare_mammal_chart, use_container_width=True) 

            if show_ACE_end_amph:
                st.altair_chart(end_amph_chart, use_container_width=True)
                
            if show_ACE_end_reptile:
                st.altair_chart(end_reptile_chart, use_container_width=True)            

            if show_ACE_end_bird:
                st.altair_chart(end_bird_chart, use_container_width=True)
                
            if show_ACE_end_mammal:
                st.altair_chart(end_mammal_chart, use_container_width=True) 
                
            if show_plant:
                st.altair_chart(plant_chart, use_container_width=True)

            if show_end_plant:
                st.altair_chart(rarity_plant_chart, use_container_width=True)
                
            if show_wetlands:
                st.altair_chart(wetlands_chart, use_container_width=True)            

            if show_farm:
                st.altair_chart(farmland_chart, use_container_width=True)
                
            if show_grazing:
                st.altair_chart(grazing_chart, use_container_width=True) 
                
            if show_DAC:
                st.altair_chart(DAC_chart, use_container_width=True)
                            
            if show_low_income:
                st.altair_chart(low_income_chart, use_container_width=True)
                 
            if show_fire:
                st.altair_chart(fire_chart, use_container_width=True)
            

st.caption("***The label 'established' is inferred from the California Protected Areas Database, which may introduce artifacts. For details on our methodology, please refer to our <a href='https://github.com/boettiger-lab/CBN-taskforce' target='_blank'>our source code</a>.", unsafe_allow_html=True)

            
st.caption("***Under California’s 30x30 framework, only GAP codes 1 and 2 are counted toward the conservation goal.") 

st.divider()

with open('app/footer.md', 'r') as file:
    footer = file.read()
st.markdown(footer)


