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



# Create the duckdb connection directly from the sqlalchemy engine instead. 
# Not as elegant as `ibis.duckdb.connect()` but shares connection with sqlalchemy.
## Create the engine
#cwd = pathlib.Path.cwd()
#connect_args = {'preload_extensions':['spatial']}
#eng = sqlalchemy.create_engine(f"duckdb:///{cwd}/duck.db",connect_args = connect_args)
#con = ibis.duckdb.from_connection(eng.raw_connection())

## Create the table from remote parquet only if it doesn't already exist on disk

con = ibis.duckdb.connect("duck.db", extensions=["spatial"])
current_tables = con.list_tables()
if "mydata" not in set(current_tables):
    tbl = con.read_parquet(ca_parquet)
    con.create_table("mydata", tbl)
ca = con.table("mydata")


for key in [
    'richness', 'rsr', 'irrecoverable_carbon', 'manageable_carbon',
    'percent_fire_10yr', 'percent_rxburn_10yr', 'percent_disadvantaged',
    'svi', 'svi_socioeconomic_status', 'svi_household_char',
    'svi_racial_ethnic_minority', 'svi_housing_transit',
    'deforest_carbon', 'human_impact'
]:
    if key not in st.session_state:
        st.session_state[key] = False
    

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

# st.header("CA 30x30 Planning & Assessment Prototype")
st.markdown("<h2>CA 30x30 Planning & Assessment Prototype</h2>", unsafe_allow_html=True)

st.markdown('<p class = "medium-font"> An interactive cloud-native geospatial tool for exploring and visualizing California\'s protected lands with open data and generative AI. </p>', unsafe_allow_html = True)


'''
- ❌ Safari/iOS not yet supported. For Safari/iOS users, try [this version](https://huggingface.co/spaces/boettiger-lab/ca-30x30-folium) with similar functionality. 
- 📊 Use the left sidebar to color-code the map by different attributes **(Group by)**, toggle on data layers and view summary charts **(Data Layers)**, or filter data **(Filters)**.
- 💬 For a more tailored experience, query our dataset of protected areas and their precomputed mean values for each of the displayed layers, using the experimental chatbot below.
'''

st.divider()

           
m = leafmap.Map(style="positron")
#############




##### Chatbot stuff 


from pydantic import BaseModel, Field
class SQLResponse(BaseModel):
    """Defines the structure for SQL response."""
    sql_query: str = Field(description="The SQL query generated by the assistant.")
    explanation: str = Field(description="A detailed explanation of how the SQL query answers the input question.")

with open('app/system_prompt.txt', 'r') as file:
    template = file.read()

from langchain_openai import ChatOpenAI
# os.environ["OPENAI_API_KEY"] = st.secrets["LITELLM_KEY"] 
# llm = ChatOpenAI(model="gorilla", temperature=0, base_url="https://llm.nrp-nautilus.io/")
# llm = ChatOpenAI(model = "llama3", api_key=st.secrets["LITELLM_KEY"], base_url = "https://llm.nrp-nautilus.io",  temperature=0)

llm = ChatOpenAI(model="gpt-4", temperature=0)

managers = ca.sql("SELECT DISTINCT manager FROM mydata;").execute()
names = ca.sql("SELECT name FROM mydata GROUP BY name HAVING SUM(acres) >10000;").execute()

from langchain_core.prompts import ChatPromptTemplate
prompt = ChatPromptTemplate.from_messages([
    ("system", template),
    ("human", "{input}")
]).partial(dialect="duckdb", table_info = ca.schema(), managers = managers, names = names)

structured_llm = llm.with_structured_output(SQLResponse)
few_shot_structured_llm = prompt | structured_llm

# @st.cache_data(ttl=600)  # Cache expires every 10 minutes
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
        legend_d = {cat: color for cat, color in style_options[color_choice]['stops']}
        m.add_legend(legend_dict=legend_d, position='bottom-left')
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


    
def summary_table_sql(ca, column, colors, ids): # get df for charts + df_tab for printed table 
    filters = [_.id.isin(ids)]
    combined_filter = reduce(lambda x, y: x & y, filters) #combining all the filters into ibis filter expression 
    df = get_summary(ca, combined_filter, [column], colors) # df used for charts 
    return df


chatbot_toggles = {key: False for key in [
    'richness', 'rsr', 'irrecoverable_carbon', 'manageable_carbon',
    'percent_fire_10yr', 'percent_rxburn_10yr', 'percent_disadvantaged',
    'svi', 'svi_socioeconomic_status', 'svi_household_char',
    'svi_racial_ethnic_minority', 'svi_housing_transit',
    'deforest_carbon', 'human_impact'
]}


#############


filters = {}

with st.sidebar:

    color_choice = st.radio("Group by:", style_options, key = "color", help = "Select a category to change map colors and chart groupings.")      
    colorby_vals = getColorVals(style_options, color_choice) #get options for selected color_by column 
    # alpha = st.slider("transparency", 0.0, 1.0, 0.7) 
    alpha = 0.8
    st.divider()



##### Chatbot 
with st.container():

    with st.popover("ℹ️ Example Queries"):
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
        - What is the total acreage of areas designated as easements?
        - Which GAP code has been impacted the most by fire? 
        - Who manages the land with the highest amount of irrecoverable carbon and highest social vulnerability index? 
        '''
        
        st.info('If the map appears blank, queried data may be too small to see at the default zoom level. Check the table below the map, as query results will also be displayed there.', icon="ℹ️")


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
            

    # Justice40 Section 
    with st.expander("🌱 Climate & Economic Justice"):
        a_justice = st.slider("transparency", 0.0, 1.0, 0.07, key = "social justice")
        show_justice40 = st.toggle("Disadvantaged Communities (Justice40)", key = "percent_disadvantaged", value=chatbot_toggles['percent_disadvantaged'])
   
        if show_justice40:
            m.add_pmtiles(url_justice40, style=justice40_style, name="Justice40", opacity=a_justice, tooltip=False, fit_bounds = False)

    # SVI Section 
    with st.expander("🏡 Social Vulnerability"):
        a_svi = st.slider("transparency", 0.0, 1.0, 0.1, key = "SVI")
        show_sv = st.toggle("Social Vulnerability Index (SVI)", key = "svi", value=chatbot_toggles['svi'])
        show_sv_socio = st.toggle("Socioeconomic Status", key = "svi_socioeconomic_status", value=chatbot_toggles['svi_socioeconomic_status'])
        show_sv_household = st.toggle("Household Characteristics", key = "svi_household_char", value=chatbot_toggles['svi_household_char'])
        show_sv_minority = st.toggle("Racial & Ethnic Minority Status", key = "svi_racial_ethnic_minority", value=chatbot_toggles['svi_racial_ethnic_minority'])
        show_sv_housing = st.toggle("Housing Type & Transportation", key = "svi_housing_transit", value=chatbot_toggles['svi_housing_transit'])
        
        if show_sv:
            m.add_pmtiles(url_svi, style = get_sv_style("RPL_THEMES"), opacity=a_svi, tooltip=False, fit_bounds = False)
        
        if show_sv_socio:
            m.add_pmtiles(url_svi, style = get_sv_style("RPL_THEME1"), opacity=a_svi, tooltip=False, fit_bounds = False)
        
        if show_sv_household:
            m.add_pmtiles(url_svi, style = get_sv_style("RPL_THEME2"), opacity=a_svi, tooltip=False, fit_bounds = False)
        
        if show_sv_minority:
            m.add_pmtiles(url_svi, style = get_sv_style("RPL_THEME3"), opacity=a_svi, tooltip=False, fit_bounds = False)
        
        if show_sv_housing:
            m.add_pmtiles(url_svi, style = get_sv_style("RPL_THEME4"), opacity=a_svi, tooltip=False, fit_bounds = False)

    # Fire Section
    with st.expander("🔥 Fire"):
        a_fire = st.slider("transparency", 0.0, 1.0, 0.15, key = "fire")
        show_fire_10 = st.toggle("Fires (2013-2022)", key = "percent_fire_10yr", value=chatbot_toggles['percent_fire_10yr'])

        show_rx_10 = st.toggle("Prescribed Burns (2013-2022)", key = "percent_rxburn_10yr", value=chatbot_toggles['percent_rxburn_10yr'])


        if show_fire_10:
            m.add_pmtiles(url_calfire, style=fire_style("layer2"), name="CALFIRE Fire Polygons (2013-2022)", opacity=a_fire, tooltip=False, fit_bounds = True)

        if show_rx_10:
            m.add_pmtiles(url_rxburn, style=rx_style("layer2"), name="CAL FIRE Prescribed Burns (2013-2022)", opacity=a_fire, tooltip=False, fit_bounds = True)
                    

    # HI Section 
    with st.expander("🚜 Human Impacts"):
        a_hi = st.slider("transparency", 0.0, 1.0, 0.1, key = "hi")
        show_carbon_lost = st.toggle("Deforested Carbon", key = "deforest_carbon", value=chatbot_toggles['deforest_carbon'])
        show_human_impact = st.toggle("Human Footprint", key = "human_impact", value=chatbot_toggles['human_impact'])
        
        if show_carbon_lost:
            m.add_tile_layer(url_loss_carbon, name="Deforested Carbon (2002-2022)", opacity = a_hi)
        
        if show_human_impact:
            m.add_cog_layer(url_hi, name="Human Footprint (2017-2021)", opacity = a_hi, fit_bounds=False)

    st.divider()
    st.markdown('<p class = "medium-font-sidebar"> Filters:</p>', help = "Apply filters to adjust what data is shown on the map.", unsafe_allow_html= True)
    for label in style_options: # get selected filters (based on the buttons selected)
        with st.expander(label):  
            if label == "GAP Status Code": # gap code 1 and 2 are on by default
                opts = getButtons(style_options, label, default_gap)
            else: # other buttons are not on by default.
                opts = getButtons(style_options, label) 
            filters.update(opts)
            
        selected = {k: v for k, v in filters.items() if v}
        if selected: 
            filter_cols = list(selected.keys())
            filter_vals = list(selected.values())
        else: 
            filter_cols = []
            filter_vals = []

    st.divider()
    st.markdown("""
    <p class="medium-font-sidebar">
    <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16' class='bi bi-github ' style='height:1em;width:1em;fill:currentColor;vertical-align:-0.125em;margin-right:4px;'  aria-hidden='true' role='img'><path d='M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.012 8.012 0 0 0 16 8c0-4.42-3.58-8-8-8z'></path></svg>Source Code: </p> <a href='https://github.com/boettiger-lab/ca-30x30' target='_blank'>https://github.com/boettiger-lab/ca-30x30</a>
    """, unsafe_allow_html=True)# adding github logo 

# Display CA 30x30 Data
if 'out' not in locals():
    style = get_pmtiles_style(style_options[color_choice], alpha, filter_cols, filter_vals)
    legend_d = {cat: color for cat, color in style_options[color_choice]['stops']}
    m.add_legend(legend_dict = legend_d, position = 'bottom-left')
    m.add_pmtiles(ca_pmtiles, style=style, name="CA", opacity=alpha, tooltip=True, fit_bounds = True)



column = select_column[color_choice]

select_colors = {
    "Year": year["stops"],
    "GAP Status Code": gap["stops"],
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
    df,df_tab = summary_table(ca, column, colors, filter_cols, filter_vals, colorby_vals)
else:
    df = summary_table_sql(ca, column, colors, ids)

total_percent = df.percent_protected.sum().round(2)


# charts displayed based on color_by variable
richness_chart = bar_chart(df, column, 'mean_richness', "Species Richness")
rsr_chart = bar_chart(df, column, 'mean_rsr', "Range-Size Rarity")
irr_carbon_chart = bar_chart(df, column, 'mean_irrecoverable_carbon', "Irrecoverable Carbon")
man_carbon_chart = bar_chart(df, column, 'mean_manageable_carbon', "Manageable Carbon")
fire_10_chart = bar_chart(df, column, 'mean_percent_fire_10yr', "Fires (2013-2022)")
rx_10_chart = bar_chart(df, column, 'mean_percent_rxburn_10yr',"Prescribed Burns (2013-2022)")
justice40_chart = bar_chart(df, column, 'mean_percent_disadvantaged', "Disadvantaged Communities (Justice40)")
svi_chart = bar_chart(df, column, 'mean_svi', "Social Vulnerability Index")
svi_socio_chart = bar_chart(df, column, 'mean_svi_socioeconomic_status', "SVI - Socioeconomic Status")
svi_house_chart = bar_chart(df, column, 'mean_svi_household_char', "SVI - Household Characteristics")
svi_minority_chart = bar_chart(df, column, 'mean_svi_racial_ethnic_minority', "SVI - Racial and Ethnic Minority")
svi_transit_chart = bar_chart(df, column, 'mean_svi_housing_transit', "SVI - Housing Type and Transit")
carbon_loss_chart = bar_chart(df, column, 'mean_carbon_lost', "Deforested Carbon (2002-2022)")
hi_chart = bar_chart(df, column, 'mean_human_impact', "Human Footprint (2017-2021)")


main = st.container()

with main:
    map_col, stats_col = st.columns([2,1])

    with map_col:
        m.to_streamlit(height=650)
        if 'out' not in locals():
            st.dataframe(df_tab, use_container_width = True)
        else:
            st.dataframe(out, use_container_width = True)

    with stats_col:
        with st.container():
            
            st.markdown(f"{total_percent}% CA Covered", help = "Updates based on displayed data")
            st.altair_chart(area_plot(df, column), use_container_width=True)
                
            if show_richness:
                # "Species Richness"
                st.altair_chart(richness_chart, use_container_width=True)

            if show_rsr:
                # "Range-Size Rarity"
                st.altair_chart(rsr_chart, use_container_width=True)

            if show_irrecoverable_carbon:
                # "Irrecoverable Carbon"
                st.altair_chart(irr_carbon_chart, use_container_width=True)

            if show_manageable_carbon:
                # "Manageable Carbon"
                st.altair_chart(man_carbon_chart, use_container_width=True)

            if show_fire_10:
                # "Fires (2013-2022)"
                st.altair_chart(fire_10_chart, use_container_width=True)
                
            if show_rx_10:
                # "Prescribed Burns (2013-2022)"
                st.altair_chart(rx_10_chart, use_container_width=True)

            if show_justice40:
                # "Disadvantaged Communities (Justice40)"
                st.altair_chart(justice40_chart, use_container_width=True)
                
            if show_sv:
                # "Social Vulnerability Index"
                st.altair_chart(svi_chart, use_container_width=True)
                
            if show_sv_socio:
                # "SVI - Socioeconomic Status"
                st.altair_chart(svi_socio_chart, use_container_width=True)
            
            if show_sv_household:
                # "SVI - Household Characteristics"
                st.altair_chart(svi_house_chart, use_container_width=True)
            
            if show_sv_minority:
                # "SVI - Racial and Ethnic Minority"
                st.altair_chart(svi_minority_chart, use_container_width=True)
            
            if show_sv_housing:
                # "SVI - Housing Type and Transit"
                st.altair_chart(svi_transit_chart, use_container_width=True)
            
            if show_carbon_lost:
                # "Deforested Carbon (2002-2022)"
                st.altair_chart(carbon_loss_chart, use_container_width=True)

            if show_human_impact:
                # "Human Footprint (2017-2021)"
                st.altair_chart(hi_chart, use_container_width=True)





st.caption("***The label 'established' is inferred from the California Protected Areas Database, which may introduce artifacts. For details on our methodology, please refer to our code: https://github.com/boettiger-lab/ca-30x30.") 

st.caption("***Under California’s 30x30 framework, only GAP codes 1 and 2 are counted toward the conservation goal.") 



st.divider()

with open('app/footer.md', 'r') as file:
    footer = file.read()
st.markdown(footer)


