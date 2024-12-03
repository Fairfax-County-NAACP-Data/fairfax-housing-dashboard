import altair as alt
import pandas as pd
import streamlit as st 

import numbers
from streamlit_gsheets import GSheetsConnection

# https://blog.streamlit.io/drill-downs-and-filtering-with-streamlit-and-altair/

st.set_page_config(layout="wide")

worksheets = {
    'Updated':"1098718425",
    'ADUs and WDUs':'966574913'
}

try:
    # Create a connection object.
    conn = st.connection("gsheets", type=GSheetsConnection)

    df_updated = conn.read(ttl='1d', worksheet=worksheets['Updated'])
except:
    df_updated = pd.read_csv('tmp.csv')

with pd.option_context("future.no_silent_downcasting", True):  # This avoids future warning when fill with False
    df_updated['Cancelled?'] = df_updated['Cancelled?'].fillna(False).infer_objects(copy=False)

df_updated = df_updated[~df_updated['Cancelled?']].drop(columns='Cancelled?')

def is_year(x):
    return pd.notnull(x) and (isinstance(x, numbers.Number) or (isinstance(x,str) and x.isdigit())) and int(x)>1900

cols = {
    'Conceptual':'Year Conceptual (Est)',
    'Pre-Development':'Year Pre-Development (Est)',
    'Under Construction':'Year Under Construction (Est)',
    'Completed':'Year Completed',
}

years = range(int(df_updated[cols.values()].min().min()), int(df_updated[cols.values()].max().max())+1)

df_aff_housing = pd.DataFrame(0, index=years, columns=cols.keys())

for _, row in df_updated.T.items():
    for j, (k,col) in enumerate(cols.items()):
        if pd.notnull(row[col]):
            c = '# of Completed Homes 60% AMI and Below' if pd.notnull(row['Year Completed']) else '# of Homes in Pipeline 60% AMI and Below'
            if pd.isnull(row[c]) and row['Property/Organization']=='Crescent':
                continue
            assert pd.notnull(row[c])
            next_years = row[list(cols.values())[j+1:]].tolist()
            next_years = [x for x in next_years if pd.notnull(x)]
            if len(next_years)==0:
                # In this state for the rest of the current years
                df_aff_housing.loc[int(row[col]):, k]+=row[c]
            else:  # Apply for year range
                df_aff_housing.loc[int(row[col]):int(min(next_years))-1, k]+=row[c]

df_aff_housing.index.name = 'Year'
df_aff_housing = df_aff_housing.reset_index()

# Convert columns that contain counts to a single row where the column names are a new column
df = df_aff_housing.melt(id_vars=['Year'],
                                    value_vars=cols.keys(),
                                    var_name="Status",
                                    value_name="Count").fillna(0)
# df['YearBinStart'] = df['Year'].apply(lambda x: f"{x-1}-01-01")
df['YearBinMid'] = df['Year'].apply(lambda x: f"{x}-01-01")
df['Count'] = df['Count'].astype(int)
df['StackOrder'] = df['Status'].apply(lambda x: 3-list(cols.keys()).index(x))
df['Opacity'] = df['Status'].apply(lambda x: 1.0 if x=='Completed' else 0.5)

regions = ["LATAM", "EMEA", "NA", "APAC"]
colors = [
    "#aa423a",
    "#f6b404",
    "#327a88",
    "#303e55",
    "#c7ab84",
    "#b1dbaa",
    "#feeea5",
    "#3e9a14",
    "#6e4e92",
    "#c98149",
    "#d1b844",
    "#8db6d8",
]

bar = (
    (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X(
                field="YearBinMid",
                type='temporal',
                title=None,
                timeUnit='year',
                bandPosition=1.0
            ),
            y=alt.Y(
                field="Count",
                type="quantitative",
                aggregate="sum",
                title="# of Homes",
            ),
            color=alt.Color(
                "Status",
                type="nominal",
                # title="Regions",
                scale=alt.Scale(range=colors),
                legend=alt.Legend(
                    direction="vertical",
                    symbolType="square",
                    tickCount=4,
                    title='# of Homes Up to 60% AMI',
                    labelLimit=0,
                    titleLimit=0
                ),
            ),
            order={"field": "StackOrder"},
            tooltip=[alt.Tooltip(field='Status'),
                     alt.Tooltip(field='Year', type='nominal'),
                     alt.Tooltip(field='Count', title='# of Homes')],
            opacity=alt.Opacity(field='Opacity', legend=None)
        )
    ).properties(width=300, title="# of Affordable Houses")   
)

line_data = [{'Prediction':'2034 Affordable Housing Goal', 'Year': '2019-01-01', 'Count': 0},
            {'Prediction':'2034 Affordable Housing Goal', 'Year': '2034-01-01', 'Count': 10000}]


line_df = pd.DataFrame(line_data)
line_aff_goal = alt.Chart(line_df).mark_line(strokeDash=[8,8]).encode(
    x=alt.X(
        field="Year",
        type='temporal',
        timeUnit='yearmonthdate',
        title=None,
        ),
    y=alt.Y(
        field="Count",
        type="quantitative",
    ),
    color=alt.Color(
                "Prediction",
                title='Board of Supervisors',
                type='nominal',
                scale=alt.Scale(domain=list(line_df['Prediction'].unique()), range=["black", "red"]),
                legend=alt.Legend(
                    direction="vertical",
                    tickCount=4,
                    labelLimit=0,
                    titleLimit=0
                ),
            ),
)

line_data = []

df_completed = df[df['Status']=='Completed']
for k in df_completed.index:
    line_data.append({'Prediction':'With Completed Affordable Housing', 
                      'Year': f"{df_completed.loc[k, 'Year']}-01-01", 
                      'Count': 31630-df_completed.loc[k, 'Count'] + 18622*(df_completed.loc[k, 'Year']-2019)/(2034-2019)})
    last_num_homes = df_completed.loc[k, 'Count']
    
last_year = int(line_data[-1]['Year'][:4])
last_est = line_data[-1]['Count']
for y in range(last_year, 2035):
    line_data.append({'Prediction':'If County Goal Met', 
                      'Year': f"{y}-01-01", 
                      'Count': 31630 - last_num_homes - (10000-last_num_homes)*(y-last_year)/(2034-last_year)+18622*(y-2019)/(2034-2019)})

    
line_df = pd.DataFrame(line_data)
line_housing_gap = alt.Chart(line_df).mark_line(strokeDash=[8,8]).encode(
    x=alt.X(
        field="Year",
        type='temporal',
        timeUnit='binnedyear',
        title=None,
        ),
    y=alt.Y(
        field="Count",
        type="quantitative",
    ),
    color=alt.Color(
                "Prediction",
                title=['Affordable Housing Affect on','Predicted up to 80% AMI Housing Gap'],
                type='nominal',
                legend=alt.Legend(
                    direction="vertical",
                    tickCount=4,
                    labelLimit=0,
                    titleLimit=0
                ),
            ),
)

# Resolve scale results in multiple legends instead of a shared one
result = (bar+line_aff_goal).resolve_scale(color='independent')

st.altair_chart(result|line_housing_gap)

st.write('This is a prototype dashboard using data from Fairfax County. It is for demonstrative purposes only.')
st.write('Hover over bar chart to see values.')
st.write("Left plot shows completed affordable (up to 60% AMI) housing and pipeline data versus the county's goal of 10000 homes by 2034. We are not currently on track to meet this goal.")
st.markdown('The right plot shows a line starting from the up to **80%** AMI housing gap that Virginia Tech estimated in 2019. The line shows the affect '+
            'on this gap due to (A) the prediction that there will be 18622 additional families under 80% AMI in 2034, (B) the currently completed <60% AMI affordable '+
            'housing, and (C) if the County meets its <60% AMI housing goal. It does not include housing built in the 60-80% AMI range which is not tracked '+
            'in the sources I have seen')