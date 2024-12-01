from streamlit.components.v1 import html
import pandas as pd
from ipyvizzu import Data, Config, Style
from ipyvizzustory import Story, Slide, Step
import ssl
import streamlit as st 

import numbers
from streamlit_gsheets import GSheetsConnection


ssl._create_default_https_context = ssl._create_unverified_context  

st.set_page_config(page_title='World Population Streamlit Story', layout='centered')
st.title('World Population Forecast')
st.header('An interactive ipyvizzu-story in Streamlit')

width=750
height=450

use_my_df = True
if not use_my_df:
     df = pd.read_csv('Data/worldpop.csv', dtype={'Year': str})
     df = df[['Year','Medium']]
else:
    worksheets = {
        'Updated':"1098718425",
        'ADUs and WDUs':'966574913'
    }

    # Create a connection object.
    conn = st.connection("gsheets", type=GSheetsConnection)

    df_updated = conn.read(ttl='1d', worksheet=worksheets['Updated'])

    with pd.option_context("future.no_silent_downcasting", True):  # This avoids future warning when fill with False
        df_updated['Cancelled?'] = df_updated['Cancelled?'].fillna(False).infer_objects(copy=False)

    df_updated = df_updated[~df_updated['Cancelled?']].drop(columns='Cancelled?')

    def is_year(x):
        return pd.notnull(x) and (isinstance(x, numbers.Number) or (isinstance(x,str) and x.isdigit())) and int(x)>1900

    cols = {
        'Completed':'Year Completed',
        'Under Construction':'Year Under Construction (Est)', 
        'Pre-Development':'Year Pre-Development (Est)', 
        'Conceptual':'Year Conceptual (Est)'
    }

    years = range(int(df_updated[cols.values()].min().min()), int(df_updated[cols.values()].max().max())+1)

    df_aff_housing = pd.DataFrame(index=years, columns=cols.keys())

    avail = pd.Series(True, index=df_updated.index)
    for k,v in cols.items():
        c = '# of Completed Homes 60% AMI and Below' if k=='Completed' else '# of Homes in Pipeline 60% AMI and Below'
        # Group rows by year and sum the # of completed homes
        df_aff_housing[k] = df_updated[avail].groupby(v).sum()[c]
        avail = avail & df_updated[v].isnull()

    # Completed houses are completed forever
    df_aff_housing.loc[:, 'Completed'] = df_aff_housing['Completed'].cumsum()

    df_aff_housing.index.name = 'Year'
    df_aff_housing = df_aff_housing.reset_index()

    # Convert columns that contain counts to a single row where the column names are a new column
    df = df_aff_housing.melt(id_vars=['Year'],
                                        value_vars=cols.keys(),
                                        var_name="Status",
                                        value_name="Count").fillna(0)
    df['Year'] = df['Year'].astype(str)
    df['Count'] = df['Count'].astype(int)

    # df = pd.read_csv('Data/worldpop.csv', dtype={'Year': str})
    # columns = df.columns.tolist()
    # columns[4] = 'Count'
    # df.columns = columns
    # df['Count'] = range(0,len(df))
    # use_my_df = False

# initialize chart
data = Data()
data.add_df(df)
#@title Create the story


region_palette = ['#FE7B00FF','#FEBF25FF','#55A4F3FF','#91BF3BFF','#E73849FF','#948DEDFF']
region_palette_str = ' '.join(region_palette)

region_color = region_palette[0]

category_palette = ['#FF8080FF', '#808080FF', region_color.replace('FF','20'), '#60A0FFFF', '#80A080FF']
category_palette_str = ' '.join(category_palette)

# Define the style of the charts in the story
style = {
        'legend' : {'width' : '13em'},
        'plot': {
            'yAxis': {
                'label': {
                    'fontSize': '1em',
                    'numberFormat' : 'prefixed',
                    'numberScale':'shortScaleSymbolUS'
                },
                'title': {'color': '#ffffff00'},
            },
            'marker' :{ 
                'label' :{ 
                    'numberFormat' : 'prefixed',
                    'maxFractionDigits' : '1',
                    'numberScale':'shortScaleSymbolUS',
                }
            },
            'xAxis': {
                'label': {
                    'angle': '2.5',
                    'fontSize': '1em',
                    'paddingRight': '0em',
                    'paddingTop': '1em',
                    'numberFormat' : 'grouped',
                },
                'title': {'color': '#ffffff00'},
            },
        },
    }

story = Story(data=data)
story.set_size(width, height)

xdata = 'Year'
label = '# of Homes' if use_my_df else 'Medium'
ydata = 'Count' if use_my_df else 'Medium'
ydata2 = ['Count','Status'] if use_my_df else ['Medium','Region']
color = 'Status' if use_my_df else 'Region'

assert xdata in df
assert ydata in df
assert all([x in df for x in ydata2])
assert color in df

# Add the first slide, containing a single animation step 
# that sets the initial chart.

slide1 = Slide(
    Step(
        Config(
            {
                'x':xdata,
                'y': ydata,
                'label': ydata,
                'title': '# of Homes',
            }
        )
    )
)
# Add the slide to the story
story.add_slide(slide1)

# Show components side-by-side
slide2 = Slide(
    Step(
        Config(
            {
                'y': ydata2,
                'color': color,
                'label': None,
                'title': 'The Population of Regions 1950-2020',
            }
        ),
        Style({ 'plot.marker.colorPalette': region_palette_str })
    )
)
story.add_slide(slide2)


# Switch on the tooltip that appears when the user hovers the mouse over a chart element.
story.set_feature('tooltip', True)

html(story._repr_html_(), width=width, height=height)

st.download_button('Download HTML export', story.to_html(), file_name=f'world-population-story.html', mime='text/html')
	
