import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import pandas as pd
import cartopy.io.shapereader as shpreader
from haversine import inverse_haversine, Direction

# Read in county position data
pos_data = pd.read_csv('./data/counties.csv', delimiter=',', index_col=0)

# Read in county election data
# Data from https://doi.org/10.7910/DVN/VOQCHQ
# Data points without county FIPS code removed
all_election_data = pd.read_csv('./data/countypres_2000-2020.csv')
# Filter data to only keep years 2016 and 2020
# Dataset reports issues with Alaska data so filter those out too
# Missing data for 2020 for some counties
# County with FIPS code 46113 was assigned a new FIPS code (46102) which is changed in the downloaded data
mask = (all_election_data['year'] >= 2016) & \
       (all_election_data['state'] != 'ALASKA') &\
       (all_election_data['state'] != 'HAWAII') & \
       (all_election_data['county_fips'] != 11001) & \
       (all_election_data['county_fips'] != 51515) & \
       (all_election_data['county_fips'] != 36000)
election_data = all_election_data[mask]

# Calculate vote percentage per party
election_data['percentagevote'] = election_data['candidatevotes']/election_data['totalvotes'] * 100

# Create new dataframe to store county change results
shift = election_data[['state', 'county_name', 'county_fips']].copy()
# Drop duplicate rows (original dataframe was both 2016 and 2020)
shift = shift.drop_duplicates(['county_fips'])

# Create columns to store change for every party
shift['DEMOCRAT'] = 0.0
shift['REPUBLICAN'] = 0.0

#Create columns for latitude and longitude so everything is in the same dataframe
shift['lat'] = 0.0
shift['lon'] = 0.0

# Iterate through every county and estimate difference in vote share for two major parties
for index, row in shift.iterrows():
    county = row['county_fips']
    for party in ['DEMOCRAT', 'REPUBLICAN']:
        previous_result = election_data.loc[(election_data['year'] == 2016) &
                                            (election_data['county_fips'] == county) &
                                            (election_data['party'] == party)]['percentagevote'].values[0]
        new_result = election_data.loc[(election_data['year'] == 2020) &
                                       (election_data['county_fips'] == county) &
                                       (election_data['party'] == party)]['percentagevote'].values[0]
        # If any of the two results is nan assign zero change
        if pd.isna(new_result) or pd.isna(previous_result):
            shift.at[index, party] = 0
        else:
            shift.at[index, party] = new_result - previous_result
    # Combine lat and long values also so it's all in one dataframe
    shift.at[index, 'lat'] = pos_data.at[county, 'lat']
    shift.at[index, 'lon'] = pos_data.at[county, 'lon']

# Create pyplot figure
fig = plt.figure(figsize=(12, 8))
ax = fig.add_subplot(1, 1, 1, projection=ccrs.LambertConformal(), frameon=False)
ax.set_extent([-120, -74, 24, 50], ccrs.PlateCarree())
# Add states shape
shapename = 'admin_1_states_provinces_lakes'
states_shp = shpreader.natural_earth(resolution='110m',
                                     category='cultural', name=shapename)
ax.add_geometries(shpreader.Reader(states_shp).geometries(), ccrs.PlateCarree(),
                  facecolor='#e5e5e5', edgecolor='white', zorder=0)
transform = ccrs.PlateCarree()._as_mpl_transform(ax)
for index, row in shift.iterrows():
    # Determine arrow color
    dem_shift = shift.at[index, 'DEMOCRAT']
    rep_shift = shift.at[index, 'REPUBLICAN']
    # Check if both lost votes, then set arrow to grey
    if dem_shift<0 and rep_shift<0:
        arrow_color = 'grey'
        ax.scatter(shift.at[index, 'lon'], shift.at[index, 'lat'],
                   color=arrow_color, transform=ccrs.PlateCarree(),
                   s=0.5)
    # If at least one of them gained votes
    else:
        if dem_shift >= rep_shift:
            arrow_color = '#1460a8'
            direction = Direction.NORTHWEST
            change = dem_shift
        else:
            arrow_color = '#bb1d2a'
            direction = Direction.NORTHEAST
            change = rep_shift
        # new_lon = shift.at[index, 'lon'] + change/3 * np.cos(theta) #haversine formula
        # new_lat = shift.at[index, 'lat'] + change/3 * np.sin(theta)
        end_location = inverse_haversine((shift.at[index, 'lat'], shift.at[index, 'lon']), change*25, direction)[::-1]
        ax.annotate(" ", xytext=(shift.at[index, 'lon'], shift.at[index, 'lat']), xy=end_location,
                    arrowprops=dict(facecolor=arrow_color, edgecolor=arrow_color,
                                    width=0.2, headwidth=3, headlength=5),
                    xycoords=transform, zorder=1)
plt.tight_layout()
#plt.show()
plt.savefig('electionshiftmap.png', dpi=300)