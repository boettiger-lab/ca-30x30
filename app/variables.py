# urls for main layer 
# ca_pmtiles = "https://huggingface.co/datasets/boettiger-lab/ca-30x30/resolve/main/cpad-stats.pmtiles"
# ca_parquet = "https://huggingface.co/datasets/boettiger-lab/ca-30x30/resolve/main/cpad-stats.parquet"

ca_pmtiles = "https://huggingface.co/datasets/boettiger-lab/ca-30x30/resolve/main/ca_30x30_stats.pmtiles"
ca_parquet = "https://huggingface.co/datasets/boettiger-lab/ca-30x30/resolve/main/ca_30x30_stats.parquet"

ca_area_acres = 1.014e8 #acres 
style_choice = "GAP Status Code"


# urls for additional data layers 
url_sr = "https://huggingface.co/datasets/boettiger-lab/ca-30x30/resolve/main/species-richness-ca/{z}/{x}/{y}.png"
url_rsr = "https://huggingface.co/datasets/boettiger-lab/ca-30x30/resolve/main/range-size-rarity/{z}/{x}/{y}.png"
url_irr_carbon = "https://huggingface.co/datasets/boettiger-lab/ca-30x30/resolve/main/ca_irrecoverable_c_2018_cog.tif"
url_man_carbon = "https://huggingface.co/datasets/boettiger-lab/ca-30x30/resolve/main/ca_manageable_c_2018_cog.tif"
url_svi = "https://data.source.coop/cboettig/social-vulnerability/svi2020_us_county.pmtiles"
url_justice40 = "https://data.source.coop/cboettig/justice40/disadvantaged-communities.pmtiles"
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
    0: False,
    3: False,
    4: False,
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
        # ['None',white]
    ]
}

easement = {
    'property': 'easement',
    'type': 'categorical',
    'stops': [
        ['True', private_access_color],
        ['False', public_access_color],
        # ['None', white]
    ]
}

year = {
    'property': 'established',
    'type': 'categorical',
    'stops': [
        ['pre-2024', year2023_color],
        ['2024', year2024_color],
        # ['None',white]
    ]
}

access = {
    'property': 'access_type',
    'type': 'categorical',
    'stops': [
        ['Open Access', public_access_color],
        ['No Public Access', private_access_color],
        ['Unknown Access', "#bbbbbb"],
        ['Restricted Access', tribal_color],
        # ['None', white]

    ]
}

gap = {
    'property': 'gap_code',
    'type': 'categorical',
    'stops': [
        [1, "#26633d"],
        [2, "#879647"],
        [3, "#EE4B2B"],
        [4, "#BF40BF"]
    ]
}

status = {
    'property': 'status',
    'type': 'categorical',
    'stops': [
        ['30x30-conserved', "#26633d"],
        ['other-conserved', "#879647"],
        ['non-conserved', "#A9A9A9"]
    ]
}


# ecoregion = {
#     'property': 'ecoregion',
#     'type': 'categorical',
#     'stops': [
#         ['Sierra Nevada Foothills', "#1f77b4"],
#         ['Southern Cascades', "#ff7f0e"],
#         ['Southeastern Great Basin', "#2ca02c"],
#         ['Southern California Mountains and Valleys', "#d62728"],
#         ['Sonoran Desert', "#9467bd"],
#         ['Northwestern Basin', "#8c564b"],
#         ['Colorado Desert', "#e377c2"],
#         ['Central Valley Coast Ranges', "#7f7f7f"],
#         ['Great Valley (South)', "#bcbd22"],
#         ['Sierra Nevada', "#17becf"],
#         ['Northern California Coast Ranges', "#aec7e8"],
#         ['Northern California Interior Coast Ranges', "#ffbb78"],
#         ['Mojave Desert', "#98df8a"],
#         ['Mono', "#ff9896"],
#         ['Southern California Coast', "#c5b0d5"],
#         ['Modoc Plateau', "#c49c94"],
#         ['Klamath Mountains', "#f7b6d2"],
#         ['Northern California Coast', "#c7c7c7"],
#         ['Great Valley (North)', "#dbdb8d"],
#         ['Central California Coast', "#9edae5"],
#         ['None', "#A9A9A9"]
#     ]
# }

ecoregion = {
    'property': 'ecoregion',
    'type': 'categorical',
    'stops': [
        ['Sierra Nevada Foothills', "#1f77b4"],
        ['Southern Cascades', "#ff7f0e"],
        ['Southeastern Great Basin', "#2ca02c"],
        ['Southern CA Mountains and Valleys', "#d62728"],
        ['Sonoran Desert', "#9467bd"],
        ['Northwestern Basin', "#8c564b"],
        ['Colorado Desert', "#e377c2"],
        ['Central Valley Coast Ranges', "#7f7f7f"],
        ['Great Valley (South)', "#bcbd22"],
        ['Sierra Nevada', "#17becf"],
        ['Northern CA Coast Ranges', "#aec7e8"],
        ['Northern CA Interior Coast Ranges', "#ffbb78"],
        ['Mojave Desert', "#98df8a"],
        ['Mono', "#ff9896"],
        ['Southern CA Coast', "#c5b0d5"],
        ['Modoc Plateau', "#c49c94"],
        ['Klamath Mountains', "#f7b6d2"],
        ['Northern CA Coast', "#c7c7c7"],
        ['Great Valley (North)', "#dbdb8d"],
        ['Central CA Coast', "#9edae5"],
        ['None', "#A9A9A9"]
    ]
}



style_options = {
    "Year": year,
    "GAP Code": gap,
    "Status": status,
    "Ecoregion": ecoregion,
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

select_column = {
    "Year": "established",
    "GAP Code": "gap_code",
    "Status":  "status",
    "Ecoregion":  "ecoregion",
    "Manager Type": "manager_type",
    "Easement": "easement",
    "Access Type": "access_type"

}

