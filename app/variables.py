# urls for main layer 
# ca_parquet = "https://huggingface.co/datasets/boettiger-lab/ca-30x30/resolve/da85dd9ca1c774d4ddf821555e3c3c9e13c9b857/ca-30x30.parquet"
# ca_pmtiles = "https://huggingface.co/datasets/boettiger-lab/ca-30x30/resolve/896db6c9a37488ee7c53ee56df67b3ccfd44d150/ca-30x30.pmtiles"


# ca_parquet = 'https://minio.carlboettiger.info/public-ca30x30/ca-30x30-cbn.parquet'
# ca_pmtiles = 'https://minio.carlboettiger.info/public-ca30x30/ca-30x30-cbn.pmtiles'

ca_parquet = 'https://minio.carlboettiger.info/public-ca30x30/ca-30x30-cbn-v3.parquet'
ca_pmtiles = 'https://minio.carlboettiger.info/public-ca30x30/ca-30x30-cbn-v3.pmtiles'

ca_area_acres = 1.014e8 #acres 
ca_area_acres = 101523750.68856516
# ca_area_acres = 103179953.76086558
style_choice = "GAP Status Code"

from utils import get_url
# urls for additional data layers 
url_sr = "https://huggingface.co/datasets/boettiger-lab/ca-30x30/resolve/main/species-richness-ca/{z}/{x}/{y}.png"
url_rsr = "https://huggingface.co/datasets/boettiger-lab/ca-30x30/resolve/main/range-size-rarity/{z}/{x}/{y}.png"
url_irr_carbon = "https://huggingface.co/datasets/boettiger-lab/ca-30x30/resolve/main/ca_irrecoverable_c_2018_cog.tif"
url_man_carbon = "https://huggingface.co/datasets/boettiger-lab/ca-30x30/resolve/main/ca_manageable_c_2018_cog.tif"
url_justice40 = "https://data.source.coop/cboettig/justice40/disadvantaged-communities.pmtiles"
url_calfire = 'https://minio.carlboettiger.info/public-fire/calfire-2023.pmtiles'
url_rxburn = 'https://minio.carlboettiger.info/public-fire/calfire-rxburn-2023.pmtiles'
url_svi = 'https://minio.carlboettiger.info/public-data/social-vulnerability/2022/SVI2022_US_tract.pmtiles'


#vector data 
url_ACE_rarerank_statewide = get_url('ACE_biodiversity/ACE_rarerank_statewide','ACE_rarerank_statewide.pmtiles')
url_ACE_rarerank_ecoregion = get_url('ACE_biodiversity/ACE_rarerank_ecoregion','ACE_rarerank_ecoregion.pmtiles')
url_ACE_biorank_statewide = get_url('ACE_biodiversity/ACE_biorank_statewide','ACE_biorank_statewide.pmtiles')
url_ACE_biorank_ecoregion = get_url('ACE_biodiversity/ACE_biorank_ecoregion','ACE_biorank_ecoregion.pmtiles')

url_ACE_amph_richness = get_url('ACE_biodiversity/ACE_amphibian_richness','ACE_amphibian_richness.pmtiles')
url_ACE_reptile_richness = get_url('ACE_biodiversity/ACE_reptile_richness','ACE_reptile_richness.pmtiles')
url_ACE_bird_richness = get_url('ACE_biodiversity/ACE_bird_richness','ACE_bird_richness.pmtiles')
url_ACE_mammal_richness = get_url('ACE_biodiversity/ACE_mammal_richness','ACE_mammal_richness.pmtiles')
url_ACE_rare_amphibian_richness = get_url('ACE_biodiversity/ACE_rare_amphibian_richness','ACE_rare_amphibian_richness.pmtiles')
url_ACE_rare_reptile_richness = get_url('ACE_biodiversity/ACE_rare_reptile_richness','ACE_rare_reptile_richness.pmtiles')
url_ACE_rare_bird_richness = get_url('ACE_biodiversity/ACE_rare_bird_richness','ACE_rare_bird_richness.pmtiles')
url_ACE_rare_mammal_richness = get_url('ACE_biodiversity/ACE_rare_mammal_richness','ACE_rare_mammal_richness.pmtiles')
url_ACE_endemic_amphibian_richness = get_url('ACE_biodiversity/ACE_endemic_amphibian_richness','ACE_endemic_amphibian_richness.pmtiles')
url_ACE_endemic_reptile_richness = get_url('ACE_biodiversity/ACE_endemic_reptile_richness','ACE_endemic_reptile_richness.pmtiles')
url_ACE_endemic_bird_richness = get_url('ACE_biodiversity/ACE_endemic_bird_richness','ACE_endemic_bird_richness.pmtiles')
url_ACE_endemic_mammal_richness = get_url('ACE_biodiversity/ACE_endemic_mammal_richness','ACE_endemic_mammal_richness.pmtiles')

url_wetlands = get_url('Freshwater_resources/Wetlands','CA_wetlands.pmtiles')
url_fire = get_url('Climate_risks/Historical_fire_perimeters','calfire_2023.pmtiles')
url_farmland = get_url('NBS_agriculture/Farmland','Farmland_2018.pmtiles')
url_grazing = get_url('NBS_agriculture/Lands_suitable_grazing','Grazing_land_2018.pmtiles')
url_DAC = get_url('Progress_data_new_protection/DAC','DAC_2022.pmtiles')
url_low_income = get_url('Progress_data_new_protection/Low_income_communities','low_income_CalEnviroScreen4.pmtiles')

# raster data
url_climate_zones = get_url('Climate_zones', 'climate_zones_10_processed_COG.tif')
url_habitat = get_url('Habitat', 'CWHR13_2022_processed_COG.tif')
url_plant_richness = get_url('Biodiversity_unique/Plant_richness', 'species_D_processed_COG.tif')
url_endemic_plant_richness = get_url('Biodiversity_unique/Rarityweighted_endemic_plant_richness', 'endemicspecies_E_processed_COG.tif')
url_resilient_conn_network = get_url('Connectivity_resilience/Resilient_connected_network_allcategories', 
                                 'rcn_wIntactBioCat_caOnly_2020-10-27_processed_COG.tif')



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


# github logo 
github_logo = 'M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.012 8.012 0 0 0 16 8c0-4.42-3.58-8-8-8z'
github_html = f"""
    <span class='medium-font-sidebar'>
        <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16' class='bi bi-github ' 
            style='height:1em;width:1em;fill:currentColor;vertical-align:-0.125em;margin-right:4px;'  
            aria-hidden='true' role='img'>
            <path d='{github_logo}'></path>
        </svg>
        <span>Source Code:</span>
        <a href='https://github.com/boettiger-lab/ca-30x30' target='_blank'>https://github.com/boettiger-lab/ca-30x30</a>
    </span>
"""


# gap codes 3 and 4 are off by default. 
default_boxes = {
    0: False,
    # 3: False,
    # 4: False,
    # "other-conserved":False,
    # "unknown":False,
    # "non-conserved":False
}

# Maplibre styles. (should these be functions?)
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
        ['HOA', hoa_color],
    ],
    'default': white
}


easement = {
    'property': 'easement',
    'type': 'categorical',
    'stops': [
        ['True', private_access_color],
        ['False', public_access_color],
    ],
    'default': white
}

year = {
    'property': 'established',
    'type': 'categorical',
    'stops': [
        ['pre-2024', year2023_color],
        ['2024', year2024_color],
    ],
    'default': white
}

access = {
    'property': 'access_type',
    'type': 'categorical',
    'stops': [
        ['Open Access', public_access_color],
        ['No Public Access', private_access_color],
        ['Unknown Access', "#bbbbbb"],
        ['Restricted Access', tribal_color],
    ],
    'default': white
}

gap = {
    'property': 'gap_code',
    'type': 'categorical',
    'stops': [
        [1, "#26633d"],
        [2, "#879647"],
        [3, "#bdcf72"],
        [4, "#6d6e6d"]
    ],
    'default': white
}

status = {
    'property': 'status',
    'type': 'categorical',
    'stops': [
        ['30x30-conserved', "#56711f"],
        ['other-conserved', "#b6ce7a"],
        ['unknown', "#e5efdb"],
        ['non-conserved', "#e1e1e1"]
        # ['non-conserved', white]

    ],
}



ecoregion = {
    'property': 'ecoregion',
    'type': 'categorical',
    'stops': [
        ['Southeastern Great Basin', "#2ca02c"],
        ['Mojave Desert', "#98df8a"],
        ['Sonoran Desert', "#9467bd"],
        ['Sierra Nevada', "#17becf"],
        ['Southern California Mountains and Valleys', "#d62728"],
        ['Mono', "#ff9896"],
        ['Central California Coast', "#9edae5"],
        ['Klamath Mountains', "#f7b6d2"],
        ['Northern California Coast', "#c7c7c7"],
        ['Northern California Coast Ranges', "#aec7e8"],
        ['Northwestern Basin and Range', "#8c564b"],
        ['Colorado Desert', "#e377c2"],
        ['Central Valley Coast Ranges', "#7f7f7f"],
        ['Southern California Coast', "#c5b0d5"],
        ['Sierra Nevada Foothills', "#1f77b4"],
        ['Southern Cascades', "#ff7f0e"],
        ['Modoc Plateau', "#c49c94"],
        ['Great Valley (South)', "#bcbd22"],
        ['Northern California Interior Coast Ranges', "#ffbb78"],
        ['Great Valley (North)', "#dbdb8d"],
    ],
    'default': white
}


climate_zone = {
    'property': 'climate_zone',
    'type': 'categorical',
    'stops': [
        [1.0, "#2ca02c"],
        [2.0, "#98df8a"],
        [3.0, "#9467bd"],
        [4.0, "#17becf"],
        [5.0, "#d62728"],
        [6.0, "#ff9896"],
        [7.0, "#dbdb8d"],
        [8.0, "#bcbd22"],
        [9.0, "#c5b0d5"],
        [10.0, "#e377c2"],
    ],
    'default': white
}

ecoregion = {
    'property': 'ecoregion',
    'type': 'categorical',
    'stops': [
        ['Southeastern Great Basin', "#2ca02c"],
        ['Mojave Desert', "#98df8a"],
        ['Sonoran Desert', "#9467bd"],
        ['Sierra Nevada', "#17becf"],
        ['Southern California Mountains and Valleys', "#d62728"],
        ['Mono', "#ff9896"],
        ['Central California Coast', "#9edae5"],
        ['Klamath Mountains', "#f7b6d2"],
        ['Northern California Coast', "#c7c7c7"],
        ['Northern California Coast Ranges', "#aec7e8"],
        ['Northwestern Basin and Range', "#8c564b"],
        ['Colorado Desert', "#e377c2"],
        ['Central Valley Coast Ranges', "#7f7f7f"],
        ['Southern California Coast', "#c5b0d5"],
        ['Sierra Nevada Foothills', "#1f77b4"],
        ['Southern Cascades', "#ff7f0e"],
        ['Modoc Plateau', "#c49c94"],
        ['Great Valley (South)', "#bcbd22"],
        ['Northern California Interior Coast Ranges', "#ffbb78"],
        ['Great Valley (North)', "#dbdb8d"],
    ],
    'default': white
}

habitat_type = {
    'property': 'habitat_type',
    'type': 'categorical',
    'stops': [
        ['Agriculture', "#2ca02c"],
        ['Conifer Forest', "#98df8a"],
        ['Conifer Woodland', "#9467bd"],
        ['Desert Shrub', "#bcbd22"],
        ['Desert Woodland', "#d62728"],
        ['Hardwood Forest', "#ff9896"],
        ['Hardwood Woodland', "#8c564b"],
        ['Herbaceous', "#f7b6d2"],
        ['Barren/Other', "#c7c7c7"],
        ['Shrub', "#aec7e8"],
        ['Wetland', "#9edae5"],
        ['Water', "#17becf"],
        ['Urban', "#ffbb78"],
    ],
    'default': white
}

networks = {
    'property': 'resilient_connected_network',
    'type': 'categorical',
    'stops': [
        [110, "#54a0f7"],
        [103, "#72b3fd"],
        [1010, "#6b9ad3"],
        [1100, "#a2b0d5"],
        [1110, "#bfd1ff"],
        [10000, "#a87001"],
        [10010, "#d09514"],
        [20000, "#ffa807"],
        [20010, "#fed087"],
        [30000, "#88cc6a"],
        [30010, "#257202"],
        [40000, "#e377c2"],
        [0, "#ffffff"],
    ],
    'default': white
}


style_options = {
    "30x30 Status": status,
    "GAP Code": gap,
    "Year": year,
    "Ecoregion": ecoregion,
    "Climate Zone": climate_zone,
    "Habitat Type": habitat_type,
    "Manager Type": manager,
    "Easement": easement,
    "Access Type": access,
    "Networks": networks,

}

# justice40_fill = {
#     'property': 'Disadvan',
#     'type': 'categorical',
#     'stops': [
#         [0, white], 
#         [1, justice40_color]
#     ]
# }

# justice40_style = {
#     "version": 8,
#     "sources": {
#         "source1": {
#             "type": "vector",
#             "url": "pmtiles://" + url_justice40,
#             "attribution": "Justice40"
#         }
#     },
#     "layers": [
#         {
#             "id": "layer1",
#             "source": "source1",
#             "source-layer": "DisadvantagedCommunitiesCEJST",
#             "filter": ["match", ["get", "StateName"], "California", True, False],
#             "type": "fill",
#             "paint": {
#                 "fill-color": justice40_fill,
#             }
#         }
#     ]
# }
# # fire_style = {"version": 8,
#     "sources": {
#         "source1": {
#             "type": "vector",
#             "url": "pmtiles://" + url_calfire,
#             "attribution": "CAL FIRE"
#         }
#     },
#     "layers": [
#         {
#             "id": "fire",
#             "source": "source1",
#             "source-layer": 'calfire2023',
#             "filter": [">=", ["get", "YEAR_"], 2013],

#             "type": "fill",
#             "paint": {
#                 "fill-color": "#D22B2B",
#             }
#         }
#     ]
# }
# rx_style = {
#     "version": 8,
#     "sources": {
#         "source2": {
#             "type": "vector",
#             "url": "pmtiles://" + url_rxburn,
#             "attribution": "CAL FIRE"
#         }
#     },
#     "layers": [
#         {
#             "id": "rxburn",
#             "source": "source2",
#             "source-layer": 'calfirerxburn2023',
#             "filter": [">=", ["get", "YEAR_"], 2013],
#             "type": "fill",
#             "paint": {
#                 "fill-color": "#702963",
#             }
#         }
#     ]
# }


# svi_style = {
#         "layers": [
#             {
#                 "id": "svi",
#                 "source": "svi",
#                 "source-layer": "svi",
#                 "filter": ["match", ["get", "ST_ABBR"], "CA", True, False],
#                 "type": "fill",
#                 "paint": {
#                     "fill-color": [
#                         "interpolate", ["linear"], ["get", "RPL_THEMES"],
#                         0, white,
#                         1, svi_color
#                     ]
#                 }
#             }
#         ]
#     }


    

select_column = {
    "30x30 Status":  "status",
    "GAP Code": "gap_code",
    "Year": "established",
    "Ecoregion":  "ecoregion",
    "Climate Zone":  "climate_zone",
    "Habitat Type":  "habitat_type",
    "Manager Type": "manager_type",
    "Easement": "easement",
    "Access Type": "access_type",
    "Networks": "resilient_connected_network",

}

