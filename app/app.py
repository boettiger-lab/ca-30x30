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

# urls for main layer 
ca_pmtiles = "https://huggingface.co/datasets/boettiger-lab/ca-30x30/resolve/main/cpad-stats.pmtiles"
ca_parquet = "https://huggingface.co/datasets/boettiger-lab/ca-30x30/resolve/main/cpad-stats.parquet"
#ca_parquet = "cpad-stats.parquet" #local copy is faster

ca_area_acres = 1.014e8 #acres 
style_choice = "GAP Status Code"




## Create the engine
cwd = pathlib.Path.cwd()
connect_args = {'preload_extensions':['spatial']}
eng = sqlalchemy.create_engine(f"duckdb:///{cwd}/duck.db",connect_args = connect_args)

# Create the duckdb connection directly from the sqlalchemy engine instead. 
# Not as elegant as `ibis.duckdb.connect()` but shares connection with sqlalchmey.
con = ibis.duckdb.from_connection(eng.raw_connection())

## Create the table from remote parquet only if it doesn't already exist on disk
current_tables = con.list_tables()
if "mydata" not in set(current_tables):
    tbl = con.read_parquet(ca_parquet)
    con.create_table("mydata", tbl)

ca = con.table("mydata")

# urls for additional data layers 
url_sr = "https://huggingface.co/datasets/boettiger-lab/ca-30x30/resolve/main/species-richness-ca/{z}/{x}/{y}.png"
url_rsr = "https://huggingface.co/datasets/boettiger-lab/ca-30x30/resolve/main/range-size-rarity/{z}/{x}/{y}.png"
url_irr_carbon = "https://huggingface.co/datasets/boettiger-lab/ca-30x30/resolve/main/ca_irrecoverable_c_2018_cog.tif"
url_man_carbon = "https://huggingface.co/datasets/boettiger-lab/ca-30x30/resolve/main/ca_manageable_c_2018_cog.tif"
url_svi = "https://data.source.coop/cboettig/social-vulnerability/svi2020_us_county.pmtiles"
url_justice40 = "https://data.source.coop/cboettig/justice40/disadvantaged-communities.pmtiles"
url_loss_carbon = "https://huggingface.co/datasets/boettiger-lab/ca-30x30/resolve/main/deforest-carbon-ca/{z}/{x}/{y}.png"
url_hi = "https://huggingface.co/datasets/boettiger-lab/ca-30x30/resolve/main/ca_human_impact_cog.tif"
url_calfire = "https://huggingface.co/datasets/boettiger-lab/ca-30x30/resolve/main/cal_fire_2022.pmtiles"
url_rxburn = "https://huggingface.co/datasets/boettiger-lab/ca-30x30/resolve/main/cal_rxburn_2022.pmtiles"

# colors for plotting 
private_access_color = "#DE881E" # orange 
public_access_color = "#3388ff" # blue
tribal_color = "#BF40BF" # purple
mixed_color = "#005a00" # green
year2023_color = "#26542C" # green
year2024_color = "#F3AB3D" # orange 
federal_color = "#529642" # green
state_color = "#A1B03D" # light green
local_color = "#365591" # blue
special_color = "#0096FF" # blue
private_color = "#7A3F1A" # brown
joint_color = "#DAB0AE" # light pink
county_color = "#DE3163" # magenta
city_color = "#ADD8E6" #light blue
hoa_color = "#A89BBC" # purple
nonprofit_color =  "#D77031" #orange
justice40_color =  "#00008B" #purple
svi_color = "#1bc7c3" #cyan
white =  "#FFFFFF" 


# gap codes 3 and 4 are off by default. 
default_gap = {
    3: False,
    4: False,
}


for key in [
    'richness', 'rsr', 'irrecoverable_carbon', 'manageable_carbon',
    'percent_fire_10yr', 'percent_rxburn_10yr', 'percent_disadvantaged',
    'svi', 'svi_socioeconomic_status', 'svi_household_char',
    'svi_racial_ethnic_minority', 'svi_housing_transit',
    'deforest_carbon', 'human_impact'
]:
    if key not in st.session_state:
        st.session_state[key] = False



from functools import reduce

def get_summary(ca, combined_filter, column, colors=None): #summary stats, based on filtered data 
    df = ca.filter(combined_filter)
    df = (df
            .group_by(*column)  # unpack the list for grouping
            .aggregate(percent_protected=100 * _.acres.sum() / ca_area_acres,
                       mean_richness = (_.richness * _.acres).sum() / _.acres.sum(),
                       mean_rsr = (_.rsr * _.acres).sum() / _.acres.sum(),
                       mean_irrecoverable_carbon = (_.irrecoverable_carbon * _.acres).sum() / _.acres.sum(),
                       mean_manageable_carbon = (_.manageable_carbon * _.acres).sum() / _.acres.sum(),
                       mean_percent_fire_10yr = (_.percent_fire_10yr *_.acres).sum()/_.acres.sum(),
                       mean_percent_rxburn_10yr = (_.percent_rxburn_10yr *_.acres).sum()/_.acres.sum(),
                       mean_percent_disadvantaged =  (_.percent_disadvantaged * _.acres).sum() / _.acres.sum(),
                       mean_svi =  (_.svi * _.acres).sum() / _.acres.sum(),
                       mean_svi_socioeconomic_status =  (_.svi_socioeconomic_status * _.acres).sum() / _.acres.sum(),
                       mean_svi_household_char =  (_.svi_household_char * _.acres).sum() / _.acres.sum(),
                       mean_svi_racial_ethnic_minority =  (_.svi_racial_ethnic_minority * _.acres).sum() / _.acres.sum(),
                       mean_svi_housing_transit =  (_.svi_housing_transit * _.acres).sum() / _.acres.sum(),
                       mean_carbon_lost = (_.deforest_carbon * _.acres).sum() / _.acres.sum(),
                       mean_human_impact =  (_.human_impact * _.acres).sum() / _.acres.sum(),
                      )
            .mutate(percent_protected=_.percent_protected.round(1))
         )
    if colors is not None and not colors.empty: #only the df will have colors, df_tab doesn't since we are printing it.
        df = df.inner_join(colors, column) 
    df = df.cast({col: "string" for col in column})
    df = df.to_pandas()
    return df


def summary_table(column, colors, filter_cols, filter_vals,colorby_vals): # get df for charts + df_tab for printed table
    filters = [] 
    if filter_cols and filter_vals: #if a filter is selected, add to list of filters 
        for filter_col, filter_val in zip(filter_cols, filter_vals):
            if len(filter_val) > 1:
                filters.append(getattr(_, filter_col).isin(filter_val))
            else:
                filters.append(getattr(_, filter_col) == filter_val[0])
    if column not in filter_cols: #show color_by column in table by adding it as a filter (if it's not already a filter)
        filter_cols.append(column)
        filters.append(getattr(_, column).isin(colorby_vals[column])) 
    combined_filter = reduce(lambda x, y: x & y, filters) #combining all the filters into ibis filter expression 
    df = get_summary(ca, combined_filter, [column], colors) # df used for charts 
    df_tab = get_summary(ca, combined_filter, filter_cols, colors = None) #df used for printed table
    return df, df_tab 



def area_plot(df, column): #percent protected pie chart 
    base = alt.Chart(df).encode(
        alt.Theta("percent_protected:Q").stack(True),
    )
    pie = ( base
           .mark_arc(innerRadius= 40, outerRadius=100)
           .encode(alt.Color("color:N").scale(None).legend(None),
                   tooltip=['percent_protected', column])
    )
    text = ( base
            .mark_text(radius=80, size=14, color="white")
            .encode(text = column + ":N")
    )
    plot = pie # pie + text
    return plot.properties(width="container", height=290)


def bar_chart(df, x, y, title): #display summary stats for color_by column 

    #axis label angles / chart size
    if x == "manager_type": #labels are too long, making vertical 
        angle = 270
        height = 373
    else: #other labels are horizontal
        angle = 0
        height = 310

    # order of bars 
    if x == "established": # order labels in chronological order, not alphabetic. 
        sort = '-x'
    elif x == "access_type": #order based on levels of openness 
        sort=['Open', 'Restricted', 'No Public', "Unknown"] 
    elif x == "manager_type": 
        sort = ["Federal","Tribal","State","Special District", "County", "City", "HOA","Joint","Non Profit","Private","Unknown"]
    else: 
        sort = 'x'

    x_title = next(key for key, value in select_column.items() if value == x)
    chart = alt.Chart(df).mark_bar().transform_calculate(
        access_label=f"replace(datum.{x}, ' Access', '')"  #omit access from access_type labels so it fits in frame
        ).encode(
        x=alt.X("access_label:N",
                axis=alt.Axis(labelAngle=angle, title=x_title),
                        sort=sort),  
        y=alt.Y(y, axis=alt.Axis()), 
        color=alt.Color('color').scale(None)
        ).properties(width="container", height=height, title = title
        )
    # sizing for poster 
    # ).configure_title(
    # fontSize=40  
    # ).configure_axis(
    # labelFontSize=24,  
    # titleFontSize=34   
    # )
    return chart



def getButtons(style_options, style_choice, default_gap=None): #finding the buttons selected to use as filters 
    column = style_options[style_choice]['property']
    opts = [style[0] for style in style_options[style_choice]['stops']]   
    default_gap = default_gap or {}  
    buttons = {
        name: st.checkbox(f"{name}", value=default_gap.get(name, True), key=column + str(name))
        for name in opts
    }
    filter_choice = [key for key, value in buttons.items() if value]  # return only selected
    d = {}
    d[column] = filter_choice
    return d



def getColorVals(style_options, style_choice): 
    #df_tab only includes filters selected, we need to manually add "color_by" column (if it's not already a filter). 
    column = style_options[style_choice]['property']
    opts = [style[0] for style in style_options[style_choice]['stops']]   
    d = {}
    d[column] = opts
    return d
    
manager = {
    'property': 'manager_type',
    'type': 'categorical',
    'stops': [
        ['Federal', federal_color],
        ['State', state_color],
        ['Non Profit', nonprofit_color],
        ['Special District', special_color],
        ['Unknown', "#bbbbbb"],
        ['County', county_color],
        ['City', city_color],
        ['Joint', joint_color],
        ['Tribal', tribal_color],
        ['Private', private_color],
        ['HOA', hoa_color]
    ]
}

easement = {
    'property': 'easement',
    'type': 'categorical',
    'stops': [
        ['True', private_access_color],
        ['False', public_access_color]
    ]
}

year = {
    'property': 'established',
    'type': 'categorical',
    'stops': [
        ['pre-2024', year2023_color],
        ['2024', year2024_color]
    ]
}

access = {
    'property': 'access_type',
    'type': 'categorical',
    'stops': [
        ['Open Access', public_access_color],
        ['No Public Access', private_access_color],
        ['Unknown Access', "#bbbbbb"],
        ['Restricted Access', tribal_color]
    ]
}

gap = {
    'property': 'reGAP',
    'type': 'categorical',
    'stops': [
        [1, "#26633d"],
        [2, "#879647"],
        [3, "#EE4B2B"],
        [4, "#BF40BF"]
    ]
}

style_options = {
    "Year": year,
    "GAP Status Code": gap,
    "Manager Type": manager,
    "Easement": easement,
    "Access Type": access,
}

justice40_fill = {
    'property': 'Disadvan',
    'type': 'categorical',
    'stops': [
        [0, white], 
        [1, justice40_color]
    ]
}

justice40_style = {
    "version": 8,
    "sources": {
        "source1": {
            "type": "vector",
            "url": "pmtiles://" + url_justice40,
            "attribution": "Justice40"
        }
    },
    "layers": [
        {
            "id": "layer1",
            "source": "source1",
            "source-layer": "DisadvantagedCommunitiesCEJST",
            "filter": ["match", ["get", "StateName"], "California", True, False],
            "type": "fill",
            "paint": {
                "fill-color": justice40_fill,
            }
        }
    ]
}

def fire_style(layer):
    return {"version": 8,
    "sources": {
        "source1": {
            "type": "vector",
            "url": "pmtiles://" + url_calfire,
            "attribution": "CAL FIRE"
        }
    },
    "layers": [
        {
            "id": "fire",
            "source": "source1",
            "source-layer": layer,
            "type": "fill",
            "paint": {
                "fill-color": "#D22B2B",
            }
        }
    ]
}
def rx_style(layer):
    return{
    "version": 8,
    "sources": {
        "source2": {
            "type": "vector",
            "url": "pmtiles://" + url_rxburn,
            "attribution": "CAL FIRE"
        }
    },
    "layers": [
        {
            "id": "fire",
            "source": "source2",
            "source-layer": layer,
            # "filter": [">=", ["get", "YEAR_"], year],
            "type": "fill",
            "paint": {
                "fill-color": "#702963",
            }
        }
    ]
}

def get_sv_style(column):
    return {
        "layers": [
            {
                "id": "SVI",
                "source": column, #need different "source" for multiple pmtiles layers w/ same file 
                "source-layer": "SVI2020_US_county",
                "filter": ["match", ["get", "STATE"], "California", True, False],
                "type": "fill",
                "paint": {
                    "fill-color": [
                        "interpolate", ["linear"], ["get", column],
                        0, white,
                        1, svi_color
                    ]
                }
            }
        ]
    }


def get_pmtiles_style(paint, alpha, filter_cols, filter_vals):
    filters = []
    for col, val in zip(filter_cols, filter_vals):
        filters.append(["match", ["get", col], val, True, False])
    combined_filters = ["all"] + filters
    style = {
        "version": 8,
        "sources": {
            "ca": {
                "type": "vector",
                "url": "pmtiles://" + ca_pmtiles,
            }
        },
        "layers": [
            {
                "id": "ca30x30",
                "source": "ca",
                "source-layer": "layer",
                "type": "fill",
                "filter": combined_filters,
                "paint": {
                    "fill-color": paint,
                    "fill-opacity": alpha
                }
            }
        ]
    }
    return style

st.set_page_config(layout="wide", page_title="CA Protected Areas Explorer", page_icon=":globe:")

#customizing style with CSS 
st.markdown(
    """
    <style>
        /* Customizing font size for radio text */
        div[class*="stRadio"] > label > div[data-testid="stMarkdownContainer"] > p {
            font-size: 18px;
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
            font-size: 18px; 
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
            padding-bottom: 0rem;
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


def get_pmtiles_style_llm(paint, ids):
    combined_filters = ["all", ["match", ["get", "id"], ids, True, False]]
    style = {
        "version": 8,
        "sources": {
            "ca": {
                "type": "vector",
                "url": "pmtiles://" + ca_pmtiles,
            }
        },
        "layers": [
            {
                "id": "ca30x30",
                "source": "ca",
                "source-layer": "layer",
                "type": "fill",
                "filter": combined_filters,
                "paint": {
                    "fill-color": paint,
                    "fill-opacity": 1,
                    # "fill-extrusion-height": 1000
                }
            }
        ]
    }
    return style

##### Chatbot stuff 

# langchain can also talk to this connection and see the table:
from langchain_community.utilities import SQLDatabase
db = SQLDatabase(eng, view_support=True)


from pydantic import BaseModel, Field
class SQLResponse(BaseModel):
    """Defines the structure for SQL response."""
    sql_query: str = Field(description="The SQL query generated by the assistant.")
    explanation: str = Field(description="A detailed explanation of how the SQL query answers the input question.")


from langchain.chains import create_sql_query_chain
template = '''You are an expert in SQL and an assistant for mapping and analyzing California land data. Given an input question, create a syntactically correct {dialect} query to run, and then provide an explanation of how you answered the input question.

For example:
{{
  "sql_query": "SELECT * FROM my_table WHERE condition = 'value';",
  "explanation": "This query retrieves all rows from my_table where the condition column equals 'value'."
}}

Ensure the response contains only this JSON object, with no additional text, formatting, or commentary.

# Important Details
 
    - For map-related queries (e.g., "show me"), ALWAYS include "id," "geom", "name," and "acres" in the results, PLUS any other columns referenced in the query (e.g., in conditions, calculations, or subqueries). This output structure is MANDATORY for all map-related queries.
    - ONLY use LIMIT in your SQL queries if the user specifies a quantity (e.g., 'show me 5'). Otherwise, return all matching data without a limit.
    - Wrap each column name in double quotes (") to denote them as delimited identifiers.
    - Pay attention to use only the column names you can see in the tables below. DO NOT query for columns that do not exist. 
    If the query mentions "biodiversity" without specifying a column, default to using "richness" (species richness). Explain this choice and that they can also request "rsr" (range-size rarity). 
    - If the query mentions carbon without specifying a column, use "irrecoverable carbon". Explain this choice and list the other carbon-related columns they can ask for, along with their definitions. 
    - If the query asks about the manager, use the "manager" column. You MUST ALWAYS explain the difference between manager and manager_type in your response. Clarify that "manager" refers to the name of the managing entity (e.g., an agency), while "manager_type" specifies the type of jurisdiction (e.g., Federal, State, Non Profit). Also, let the user know they can include "manager_type" in their query if they want to refine their results.
    - If the user's query is unclear, DO NOT make assumptions. Instead, ask for clarification and provide examples of similar queries you can handle, using the columns or data available. You MUST ONLY deliver accurate results.
    - If you are mapping the data, explicitly state that the data is being visualized on a map. ALWAYS include a statement encouraging the user to examine the queried data below the map, as some areas may be too small at the current zoom level. 
    - Users may not be familiar with this data, so your explanation should be short, clear, and easily understandable. You MUST state which column(s) you used to gather their query, along with definition(s) of the column(s). Do NOT explain SQL commands. 
    - If the prompt is unrelated to the California dataset, provide examples of relevant queries that you can answer.

# Example Questions and How to Approach Them 

## Example:
example_user: "Show me all non-profit land."
example_assistant: {{"sql_query": 
    SELECT id, geom, name, acres
    FROM mydata 
    WHERE "manager_type" = "Non Profit";
"explanation":"I selected all data where `manager_type` is 'Non Profit'."
}}

## Example: 
example_user: "Which gap code has been impacted the most by fire?"
example_assistant: {{"sql_query":  
    SELECT "reGAP", SUM("percent_fire_10yr") AS temp
    FROM mydata
    GROUP BY "reGAP"
    ORDER BY temp ASC
    LIMIT 1;
"explanation":"I used the `percent_fire_10yr` column, which shows the percentage of each area burned over the past 10 years (2013–2022), summing it for each GAP code to find the one with the highest total fire impact."
}}

## Example: 
example_user: "Who manages the land with the worst biodiversity and highest SVI?"
example_assistant: {{"sql_query":    
SELECT manager,richness, svi
    FROM mydata
    GROUP BY "manager"
    ORDER BY richness ASC, svi DESC
    LIMIT 1;
"explanation": "I identified the land manager with the worst biodiversity and highest Social Vulnerability Index (SVI) by analyzing the columns: `richness`, which measures species richness, and `svi`, which represents social vulnerability based on factors like socioeconomic status, household characteristics, racial & ethnic minority status, and housing & transportation.

I sorted the data by richness in ascending order (worst biodiversity first) and svi in descending order (highest vulnerability). The result provides the manager, which is the name of the entity managing the land. Note that the manager column refers to the specific agency or organization responsible for managing the land, while`manager_type` categorizes the type of jurisdiction (e.g., Federal, State, Non Profit)."
}}


## Example: 
example_user: "Show me the biggest protected area"
example_assistant: {{"sql_query":       
    SELECT "id", "geom", "name", "acres", "manager", "manager_type", "acres"
    FROM mydata
    ORDER BY "acres" DESC
    LIMIT 1;
"explanation": "I identified the biggest protected area by sorting the data in descending order based on the `acres` column, which represents the size of each area." 

## Example: 
example_user: "Show me the 50 most biodiverse areas found in disadvantaged communities."
example_assistant: {{"sql_query":   
    SELECT "id", "geom", "name", "acres", "richness", "percent_disadvantaged" FROM mydata 
    WHERE "percent_disadvantaged" > 0
    ORDER BY "richness" DESC
    LIMIT 50;
"explanation": "I used the `richness` column to measure biodiversity and the `percent_disadvantaged` column to identify areas located in disadvantaged communities. The `percent_disadvantaged` value is derived from the Justice40 initiative, which identifies communities burdened by systemic inequities and vulnerabilities across multiple domains, including climate resilience, energy access, health disparities, housing affordability, pollution exposure, transportation infrastructure, water quality, and workforce opportunities.

The results are sorted in descending order by biodiversity richness (highest biodiversity first), and only areas with a `percent_disadvantaged` value greater than 0 (indicating some portion of the area overlaps with a disadvantaged community) are included."
}}


## Example: 
example_user: "Show me federally managed gap 3 lands that are in the top 5% of biodiversity richness and have experienced forest fire over at least 50% of their area"
sql_query:  
    WITH temp_tab AS (
        SELECT PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY "richness") AS temp
        FROM mydata
    )
    SELECT "id", "geom", "name", "acres","richness", "reGAP"
    FROM mydata
    WHERE "reGAP" = 3
        AND "percent_fire_10yr" >= 0.5
        and "manager_type" = "Federal"
        AND "richness" > (SELECT temp FROM temp_tab);


## Example: 
example_user: "What is the total acreage of areas designated as easements?
sql_query:  
    SELECT SUM("acres") AS total_acres
    FROM mydata
    WHERE "easement" = "True";


# Detailed Explanation of the Columns in the California Dataset 
- "established": The time range which the land was acquired, either "2024" or "pre-2024". 
- "reGAP": The GAP status code; corresponds to the level of protection the area has. There are 4 gap codes and are defined as the following. 
    Status 1: Permanently protected to maintain a natural state, allowing natural disturbances or mimicking them through management.
    Status 2: Permanently protected but may allow some uses or management practices that degrade natural communities or suppress natural disturbances.
    Status 3: Permanently protected from major land cover conversion but allows some extractive uses (e.g., logging, mining) and protects federally listed species.
    Status 4: No protection mandates; land may be converted to unnatural habitat types or its management intent is unknown.

- "name": The name of a protected area. The user may use a shortened name and/or not capitalize it. For example, "redwoods" may refer to "Redwood National Park", or "klamath" refers to "Klamath National Forest". Another example, "san diego wildlife refuge" could refer to multiple areas, so you would use "WHERE LOWER("name") LIKE '%san diego%' AND LOWER("name") LIKE '%wildlife%' AND LOWER("name") LIKE '%refuge%';" in your SQL query, to ensure that it is case-insensitive and matches any record that includes our phrases, because we don't want to overlook a match.  If the name isn't capitalized, you MUST ensure the search is case-insensitive by converting "name" to lowercase. 
The names of the largest parks are {names}.
- "access_type": Level of access to the land: "Unknown Access","Restricted Access","No Public Access" and "Open Access". 
- "manager": The name of land manager for the area. Also referred to as the agency name. These are the manager names: {managers}. Users might use acronyms or could omit "United States" in the agency name, make sure to use the name used in the table. Some examples: "BLM" or "Bureau of Land Management" refers to the "United States Bureau of Land Management" or "CDFW" is "California Department of Fish and Wildlife". Similar to the "name" field, you can search for managers using "LIKE" in the SQL query. 
- "manager_type": The jurisdiction of the land manager: "Federal","State","Non Profit","Special District","Unknown","County","City","Joint","Tribal","Private","HOA". If the user says "non-profit", do not use a hyphen in your query. 
- "easement": Boolean value; whether or not the land is an easement. 
- "acres": Land acreage; measures the size of the area. 
- "id": unique id for each area. This is necessary for displaying queried results on a map. 
- "type": Physical type of area, either "Land" or "Water". 
- "richness": Species richness; higher values indicate better biodiversity.
- "rsr": Range-size rarity; higher values indicate better rarity metrics.
- "svi": Social Vulnerability Index based on 4 themes: socioeconomic status, household characteristics, racial & ethnic minority status, and housing & transportation. Higher values indicate greater vulnerability.
    - Themes:
        - "svi_socioeconomic_status": Poverty, unemployment, housing cost burden, education, and health insurance.
        - "svi_household_char": Age, disability, single-parent households, and language proficiency.
        - "svi_racial_ethnic_minority": Race and ethnicity variables.
        - "svi_housing_transit": Housing type, crowding, vehicles, and group quarters.
- "percent_disadvantaged": Justice40-defined disadvantaged communities overburdened by climate, energy, health, housing, pollution, transportation, water, and workforce factors. Higher values indicate more disadvantage. Range is between 0 and 1. 
- "deforest_carbon": Carbon emissions due to deforestation.
- "human_impact": A score representing the human footprint: cumulative anthropogenic impacts such as land cover change, population density, and infrastructure. 
- "percent_fire_10yr": The percentage of the area burned by fires from (2013-2022). Range is between 0 and 1. 
- "percent_rxburn_10yr": The percentage of the area affected by prescribed burns from (2013-2022). Range is between 0 and 1. 

Only use the following tables:
{table_info}.

Question: {input}'''

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


    
def summary_table_sql(column, colors, ids): # get df for charts + df_tab for printed table 
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

    
# Display CA 30x30 Data
if 'out' not in locals():
    style = get_pmtiles_style(style_options[color_choice], alpha, filter_cols, filter_vals)
    legend_d = {cat: color for cat, color in style_options[color_choice]['stops']}
    m.add_legend(legend_dict = legend_d, position = 'bottom-left')
    m.add_pmtiles(ca_pmtiles, style=style, name="CA", opacity=alpha, tooltip=True, fit_bounds = True)


select_column = {
    "Year": "established",
    "GAP Status Code": "reGAP",
    "Manager Type": "manager_type",
    "Easement": "easement",
    "Access Type": "access_type",
}

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
    df,df_tab = summary_table(column, colors, filter_cols, filter_vals, colorby_vals)
else:
    df = summary_table_sql(column, colors, ids)

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



#########


footer = st.container()



st.caption("***The label 'established' is inferred from the California Protected Areas Database, which may introduce artifacts. For details on our methodology, please refer to our code: https://github.com/boettiger-lab/ca-30x30.") 

st.caption("***Under California’s 30x30 framework, only GAP codes 1 and 2 are counted toward the conservation goal.") 



st.divider()



'''
## Credits
Authors: Cassie Buhler & Carl Boettiger, UC Berkeley
License: BSD-2-clause

Data: https://huggingface.co/datasets/boettiger-lab/ca-30x30

### Data sources
- CA Nature Terrestrial 30x30 Conserved Areas map layer by CA Nature. Data: https://www.californianature.ca.gov/datasets/CAnature::30x30-conserved-areas-terrestrial-2024/about. License: Public Domain

- Imperiled Species Richness and Range-Size-Rarity from NatureServe (2022). Data: https://beta.source.coop/repositories/cboettig/mobi. License CC-BY-NC-ND

- Irrecoverable Carbon from Conservation International, reprocessed to COG on https://beta.source.coop/cboettig/carbon, citation: https://doi.org/10.1038/s41893-021-00803-6, License: CC-BY-NC

- Fire polygons by CAL FIRE (2022), reprocessed to PMTiles on https://beta.source.coop/cboettig/fire/. License: Public Domain

- Climate and Economic Justice Screening Tool, US Council on Environmental Quality, Justice40. Description: https://screeningtool.geoplatform.gov/en/methodology#3/33.47/-97.5. Data: https://beta.source.coop/repositories/cboettig/justice40/description/, License: Public Domain

- CDC 2020 Social Vulnerability Index by US Census Tract. Description: https://www.atsdr.cdc.gov/place-health/php/svi/index.html. Data: https://source.coop/repositories/cboettig/social-vulnerability/description. License: Public Domain

- Carbon-loss by Vizzuality, on https://beta.source.coop/repositories/vizzuality/lg-land-carbon-data. Citation: https://doi.org/10.1101/2023.11.01.565036, License: CC-BY

- Human Footprint by Vizzuality, on https://beta.source.coop/repositories/vizzuality/hfp-100.  Citation: https://doi.org/10.3389/frsen.2023.1130896, License: Public Domain

'''

