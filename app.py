from flask import Flask, render_template
import pandas as pd
import plotly.express as px
import plotly.io as pio
import numpy as np
from plotly.subplots import make_subplots
import plotly.graph_objects as go

app = Flask(__name__)

# Configuration
px.defaults.color_continuous_scale = px.colors.sequential.Viridis
px.defaults.template = "plotly_white"
WHO_PM25_LIMIT = 25  # µg/m³

def load_data():
    df = pd.read_csv('data.csv')
    
    # Air quality bins (EPA standards)
    df['Air_Quality_Level'] = pd.cut(
        df['PM2.5'],
        bins=[0, 12, 35, 55, 150, np.inf],
        labels=['Good', 'Moderate', 'Unhealthy', 'Very Unhealthy', 'Hazardous']
    )
    
    # WHO compliance flag
    df['Exceeds_WHO'] = np.where(df['PM2.5'] > WHO_PM25_LIMIT, 'Exceeds', 'Within Limits')
    
    return df

@app.route('/')
def dashboard():
    df = load_data()
    
    # ----------------------------------
    # 1. WHO Compliance Pie Chart
    # ----------------------------------
    compliance = df['Exceeds_WHO'].value_counts().reset_index()
    q1_fig = px.pie(
        compliance,
        names='Exceeds_WHO',
        values='count',
        title='<b>1. WHO PM2.5 Compliance</b><br><sub>Percentage of readings exceeding 25 µg/m³ safety limit</sub>',
        color='Exceeds_WHO',
        color_discrete_map={'Exceeds': '#EF553B', 'Within Limits': '#00CC96'},
        hole=0.4
    )
    q1_fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        hovertemplate="<b>%{label}</b><br>%{value} readings (%{percent})"
    )
    q1_fig.add_annotation(
        text="WHO considers PM2.5 >25µg/m³ as unsafe for prolonged exposure",
        xref="paper", yref="paper",
        x=0.5, y=-0.2, showarrow=False
    )

    # ----------------------------------
    # 2. Industrial Proximity Impact
    # ----------------------------------
    q2_fig = px.scatter(
        df,
        x='Proximity_to_Industrial_Areas',
        y='PM2.5',
        trendline='rolling',
        trendline_options=dict(window=5),
        title='<b>2. Industrial Proximity Impact</b><br>',
        labels={
            'Proximity_to_Industrial_Areas': 'Distance to Industry (km)',
            'PM2.5': 'PM2.5 Concentration (µg/m³)'
        }
    )
    q2_fig.add_hline(
        y=WHO_PM25_LIMIT,
        line_dash="dot",
        annotation_text="WHO Safety Limit",
        line_color="red"
    )
    

    # ----------------------------------
    # 3. Population Density Relationship
    # ----------------------------------
    # 3. Population Density Relationship - IMPROVED VERSION
# 3. Simplified Population Density vs PM2.5 Line Graph
    df_sorted = df.sort_values('Population_Density')

    q3_fig = px.line(
        df_sorted,
        x='Population_Density',
        y='PM2.5',
        title='<b>3. PM2.5 Levels by Population Density</b><br>'
            '<sub>Rolling average with 95% confidence interval</sub>',
        labels={
            'Population_Density': 'Population Density (people/km²)',
            'PM2.5': 'PM2.5 Concentration (µg/m³)'
        },
        color_discrete_sequence=['#636EFA']
    )

# Add rolling average with confidence interval
    q3_fig.data[0].update(
        mode='lines',
        line=dict(width=3),
        name='Actual Readings'
    )

    q3_fig.add_trace(go.Scatter(
        x=df_sorted['Population_Density'],
        y=df_sorted['PM2.5'].rolling(20, center=True).mean(),
        line=dict(color='red', width=3),
        name='20-Point Rolling Avg',
        mode='lines'
    ))

# Add WHO safety limit
    q3_fig.add_hline(
        y=WHO_PM25_LIMIT,
        line_dash="dot",
        annotation_text="WHO Safety Limit",
        line_color="red"
    )



# Improve axis formatting
    q3_fig.update_xaxes(tickformat=",.0f")
    q3_fig.update_yaxes(tickformat=".1f")

    # ----------------------------------
    # 4. Pollutant Interactions
    # ----------------------------------
    pollutants = ['PM2.5', 'PM10', 'NO2', 'SO2', 'CO']
    q4_fig = px.imshow(
        df[pollutants].corr(),
        x=pollutants,
        y=pollutants,
        title='<b>4. Pollutant Relationships</b><br><sub>Red: Positive correlation | Blue: Negative correlation</sub>',
        color_continuous_scale='RdBu_r',
        zmin=-1,
        zmax=1
    )
    q4_fig.add_annotation(
        text="PM2.5 and PM10 frequently co-occur (r=0.82)",
        xref="paper", yref="paper",
        x=0.5, y=-0.2,
        showarrow=False
    )

    # ----------------------------------
    # 5. Weather Influence
    # ----------------------------------
    # 5. Simplified Temperature vs PM2.5 Visualization
    q5_fig = px.scatter(
        df,
        x='Temperature',
        y='PM2.5',
        title='<b>5. Temperature vs PM2.5</b><br><sub>Size shows population density | Color shows industrial proximity</sub>',
        labels={
            'Temperature': 'Temperature (°C) →',
            'PM2.5': 'PM2.5 Concentration (µg/m³) →',
            'Proximity_to_Industrial_Areas': 'Distance to Industry (km)',
            'Population_Density': 'Population Density'
        },
        size='Population_Density',
        color='Proximity_to_Industrial_Areas',
        size_max=15,
        opacity=0.7,
        color_continuous_scale='thermal'
    )

    # Add clear reference lines
    q5_fig.add_hline(
        y=WHO_PM25_LIMIT,
        line_dash="dot",
        line_color="red",
        annotation_text="WHO Safety Limit", 
        annotation_position="right"
    )



    # Improve layout
    q5_fig.update_layout(
        coloraxis_colorbar=dict(
            title="Distance to<br>Industry (km)",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.05
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    # Simplify hover data
    q5_fig.update_traces(
        hovertemplate="<b>%{x}°C</b><br>PM2.5: %{y} µg/m³<br>Pop Density: %{marker.size:,}"
    )

    # ----------------------------------
    # 6. Worst-Case Scenarios
    # ----------------------------------
    df['Risk_Quadrant'] = np.where(
        (df['PM2.5'] > df['PM2.5'].median()) & 
        (df['Population_Density'] > df['Population_Density'].median()),
        'High Risk',
        'Other'
    )
    q6_fig = px.scatter(
        df,
        x='Population_Density',
        y='PM2.5',
        color='Risk_Quadrant',
        title='<b>6. High-Risk Zones</b><br><sub>Areas with both high pollution and population density</sub>',
        color_discrete_map={'High Risk': 'red', 'Other': 'gray'},
        labels={
            'Population_Density': 'Population Density (people/km²)',
            'PM2.5': 'PM2.5 (µg/m³)'
        }
    )
    q6_fig.add_annotation(
        text=f"{len(df[df['Risk_Quadrant']=='High Risk'])} high-risk locations identified",
        xref="paper", yref="paper",
        x=0.7, y=0.1,
        bgcolor="white"
    )

    # ----------------------------------
    # 7. Secondary Pollutant Patterns
    # ----------------------------------
    # 7. Simplified Multi-Pollutant Relationships
    # 7. Simple PM2.5 vs NO2 with CO as size
    q7_fig = px.scatter(
        df,
        x='PM2.5',
        y='NO2',
        size='CO',
        color='Air_Quality_Level',
        title='<b>7. Core Pollutant Relationships</b><br>'
            '<sub>Size represents CO levels | Color shows air quality</sub>',
        labels={
            'PM2.5': 'PM2.5 (µg/m³)',
            'NO2': 'NO2 (ppb)',
            'CO': 'CO (ppm)'
        }
    )

    # Add trendline
    q7_fig.add_trace(
        go.Scatter(
            x=df['PM2.5'],
            y=np.poly1d(np.polyfit(df['PM2.5'], df['NO2'], 1))(df['PM2.5']),
            mode='lines',
            name='Trend',
            line=dict(color='gray', dash='dot')
        )
    )

    # ----------------------------------
    # 8. Safety Threshold Breaches
    # ----------------------------------
    q8_fig = px.bar(
        df['Air_Quality_Level'].value_counts(),
        title='<b>8. Air Quality Levels</b><br><sub>Distribution across EPA categories</sub>',
        labels={'value': 'Number of Readings', 'index': 'Air Quality Level'},
        color=df['Air_Quality_Level'].value_counts().index,
        color_discrete_sequence=px.colors.sequential.Viridis_r
    )
    q8_fig.add_hline(
        y=len(df[df['PM2.5'] > 150]),
        line_dash="dot",
        annotation_text="Hazardous Threshold (150 µg/m³)",
        line_color="red"
    )

    # ----------------------------------
    # 9. Humidity Effect
    # ----------------------------------
# 9. Improved Humidity Impact Visualization
# Create humidity bins
    df['Humidity_Bin'] = pd.cut(df['Humidity'], 
                            bins=[0, 30, 60, 100],
                            labels=['Low (<30%)', 'Medium (30-60%)', 'High (>60%)'])

    # Create the figure
    q9_fig = make_subplots(rows=1, cols=2, 
                        subplot_titles=("Raw Data", "Binned Averages"),
                        horizontal_spacing=0.15)

    # Left plot - Raw data with trendline
    q9_fig.add_trace(
        go.Scatter(
            x=df['Humidity'],
            y=df['PM2.5'],
            mode='markers',
            marker=dict(color='#636EFA', opacity=0.5),
            name='Individual Readings'
        ),
        row=1, col=1
    )

    # Add LOESS trendline (if statsmodels is available)
    try:
        import statsmodels.api as sm
        lowess = sm.nonparametric.lowess(df['PM2.5'], df['Humidity'], frac=0.3)
        q9_fig.add_trace(
            go.Scatter(
                x=lowess[:, 0],
                y=lowess[:, 1],
                mode='lines',
                line=dict(color='red', width=3),
                name='Trend'
            ),
            row=1, col=1
        )
    except:
        # Fallback to rolling average if statsmodels not available
        df_sorted = df.sort_values('Humidity')
        q9_fig.add_trace(
            go.Scatter(
                x=df_sorted['Humidity'],
                y=df_sorted['PM2.5'].rolling(20, center=True).mean(),
                mode='lines',
                line=dict(color='red', width=3),
                name='Rolling Avg'
            ),
            row=1, col=1
        )

    # Right plot - Binned averages
    bin_avg = df.groupby('Humidity_Bin', observed=True).agg(
        Avg_PM25=('PM2.5', 'mean'),
        Std_PM25=('PM2.5', 'std')
    ).reset_index()

    q9_fig.add_trace(
        go.Bar(
            x=bin_avg['Humidity_Bin'],
            y=bin_avg['Avg_PM25'],
            error_y=dict(array=bin_avg['Std_PM25']),
            marker_color=['#FFA15A', '#AB63FA', '#19D3F3'],
            name='Average PM2.5'
        ),
        row=1, col=2
    )

  

    # Update layout
    q9_fig.update_layout(
        title_text='<b>9. Humidity Impact on PM2.5</b><br><sub>Left: Individual readings with trend | Right: Binned averages</sub>',
        showlegend=False,
        margin=dict(t=100),
        hovermode="x unified"
    )

    # Axis labels
    q9_fig.update_xaxes(title_text="Relative Humidity (%)", row=1, col=1)
    q9_fig.update_yaxes(title_text="PM2.5 (µg/m³)", row=1, col=1)
    q9_fig.update_xaxes(title_text="Humidity Range", row=1, col=2)
    q9_fig.update_yaxes(title_text="Average PM2.5 (µg/m³)", row=1, col=2)
    # ----------------------------------
    # 10. Multi-Pollutant Hotspots
    # ----------------------------------
    q10_fig = px.scatter_3d(
        df,
        x='PM2.5',
        y='NO2',
        z='CO',
        color='Population_Density',
        title='<b>10. 3D Pollution Hotspots</b><br><sub>Locations with multiple elevated pollutants</sub>',
        labels={
            'PM2.5': 'PM2.5 (µg/m³)',
            'NO2': 'NO2 (ppb)',
            'CO': 'CO (ppm)',
            'Population_Density': 'Density (people/km²)'
        }
    )
    q10_fig.update_layout(scene=dict(
        xaxis_title='PM2.5 →',
        yaxis_title='NO2 →',
        zaxis_title='CO →'
    ))
    
    # ----------------------------------
    # Render Template
    # ----------------------------------
    return render_template(
        'index.html',
        q1_fig=pio.to_html(q1_fig, full_html=False),
        q2_fig=pio.to_html(q2_fig, full_html=False),
        q3_fig=pio.to_html(q3_fig, full_html=False),
        q4_fig=pio.to_html(q4_fig, full_html=False),
        q5_fig=pio.to_html(q5_fig, full_html=False),
        q6_fig=pio.to_html(q6_fig, full_html=False),
        q7_fig=pio.to_html(q7_fig, full_html=False),
        q8_fig=pio.to_html(q8_fig, full_html=False),
        q9_fig=pio.to_html(q9_fig, full_html=False),
        q10_fig=pio.to_html(q10_fig, full_html=False),
        stats=df.describe().round(2).to_html(classes='table table-striped')
    )

if __name__ == '__main__':
    app.run(debug=True, port=5001)