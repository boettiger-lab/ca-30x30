# urls for main layer 
ca_pmtiles = "https://huggingface.co/datasets/boettiger-lab/ca-30x30/resolve/main/cpad-stats.pmtiles"
ca_parquet = "https://huggingface.co/datasets/boettiger-lab/ca-30x30/resolve/main/cpad-stats.parquet"

ca_area_acres = 1.014e8 #acres 
style_choice = "GAP Status Code"


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

select_column = {
    "Year": "established",
    "GAP Status Code": "reGAP",
    "Manager Type": "manager_type",
    "Easement": "easement",
    "Access Type": "access_type",
}

