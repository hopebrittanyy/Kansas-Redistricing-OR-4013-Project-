#!/usr/bin/env python
# coding: utf-8

# In[39]:


#Import all the things

import gurobipy as gp
from gurobipy import GRB
import networkx as nx
from gerrychain import Graph
import geopandas as gpd


# In[41]:


#Read the KS county graph. This is where all the edges and nodes are stored in the json file

filepath = 'C:\\Users\\14053\\Documents\\OPERATIONS RESEARCH\\OR Project Data KS\\'
filename = 'KS_county.json'

G = Graph.from_json( filepath + filename )


# In[42]:


#Print the nodes

print("The Kansas county graph has this many nodes total = ", G.number_of_nodes())
print("The Kansas county graph has these nodes = ", G.nodes)


# In[43]:


#Print the edges

print("The Kansas county graph has this many edges total = ", G.number_of_edges())
print("The Kansas county graph has these edges = ", G.edges)


# In[44]:


#For each node print the node #, the county name,its population, and Lat-Long coordinates

for node in G.nodes:
    county_name = G.nodes[node]['NAME20']
    county_population = G.nodes[node]['P0010001']
    G.nodes[node]['TOTPOP'] = county_population
    
    G.nodes[node]['C_X'] = G.nodes[node]['INTPTLON20']
    G.nodes[node]['C_Y'] = G.nodes[node]['INTPTLAT20']
        
    print("Node", node, "represents", county_name, "County, which had a population of", county_population, "and is centered at (", G.nodes[node]['C_X'], ",", G.nodes[node]['C_Y'],")")


# In[45]:


pip install geopy


# In[46]:


# getting and storing distances
from geopy.distance import geodesic

dist = dict()
for i in G.nodes:
    for j in G.nodes:
        loc_i = ( G.nodes[i]['C_Y'],  G.nodes[i]['C_X'] )
        loc_j = ( G.nodes[j]['C_Y'],  G.nodes[j]['C_X'] )
        dist[i,j] = geodesic(loc_i,loc_j).miles


# In[47]:


#Impose a 1% deviation 
deviation = 0.01

import math
k = 4         # number of districts
total_population = sum(G.nodes[node]['TOTPOP'] for node in G.nodes)

L = math.ceil((1-deviation/2)*total_population/k)
U = math.floor((1+deviation/2)*total_population/k)
print("Using L =",L,"and U =",U,"and k =",k)


# In[48]:



# creating the model
m = gp.Model()

# creating the varibales
x = m.addVars(G.nodes, G.nodes, vtype=GRB.BINARY)  # this is creating a x[i,j] variable that is one when county i is 
                                                        # assigned to district centered at j 


# In[49]:



# The objective is to minimize the the moment of interia 
m.setObjective( gp.quicksum( dist[i,j]*dist[i,j]*G.nodes[i]['TOTPOP']*x[i,j] for i in G.nodes for j in G.nodes), GRB.MINIMIZE )


# In[50]:


# adding a constraint that ensures each county is assigned to a district
m.addConstrs( gp.quicksum(x[i,j] for j in G.nodes) == 1 for i in G.nodes)

# adding a constraint that ensures there should be 4 districts
m.addConstr( gp.quicksum( x[j,j] for j in G.nodes ) == k )

# adding a constraint that ensures the districts are between U and L 
m.addConstrs( gp.quicksum( G.nodes[i]['TOTPOP'] * x[i,j] for i in G.nodes) >= L * x[j,j] for j in G.nodes )
m.addConstrs( gp.quicksum( G.nodes[i]['TOTPOP'] * x[i,j] for i in G.nodes) <= U * x[j,j] for j in G.nodes )

# adding a coupling constraint stating if i is assigneed to j, then j is the center
m.addConstrs( x[i,j] <= x[j,j] for i in G.nodes for j in G.nodes )

m.update()


# In[51]:


# adding contiguity constraints
DG = nx.DiGraph(G)

# adding flow varible
f = m.addVars( DG.nodes, DG.edges, vtype=GRB.CONTINUOUS)
M = DG.number_of_nodes()-1

# node j cannot recieve a flow of its own type
m.addConstrs( gp.quicksum( f[j,u,j] for u in DG.neighbors(j) ) == 0 for j in DG.nodes )

# Add constraints saying that node i can receive flow of type j only if i is assigned to j
m.addConstrs( gp.quicksum( f[j,u,i] for u in DG.neighbors(i)) <= M * x[i,j] for i in DG.nodes for j in DG.nodes if i != j )

# If i is assigned to j, then i should consume one unit of j flow. Otherwise, i should consume no units of j flow.
m.addConstrs( gp.quicksum( f[j,u,i] - f[j,i,u] for u in DG.neighbors(i)) == x[i,j] for i in DG.nodes for j in DG.nodes if i != j )

m.update()


# In[52]:


#solve model
m.Params.MIPGap = 0.0
m.optimize()


# In[53]:


print("The moment of inertia objective is",m.objval)

# retrieve the districts and their populations
centers = [j for j in G.nodes if x[j,j].x > 0.5 ]
districts = [ [i for i in G.nodes if x[i,j].x > 0.5] for j in centers]
district_counties = [ [ G.nodes[i]["NAME20"] for i in districts[j] ] for j in range(k)]
district_populations = [ sum(G.nodes[i]["TOTPOP"] for i in districts[j]) for j in range(k) ]

# print district info
for j in range(k):
    print("District",j,"has population",district_populations[j],"and contains counties",district_counties[j])


# In[54]:


# Read Kansas county shapefile 
filepath = 'C:\\Users\\14053\\Documents\\OPERATIONS RESEARCH\\OR Project Data KS\\'
filename = 'Ks_county.shp'

# Read geopandas dataframe from file
df = gpd.read_file( filepath + filename )


# In[55]:


# Which district is each county assigned to?
assignment = [ -1 for u in G.nodes ]
    
# for each district j
for j in range(len(districts)):
    
    # for each node i in this district
    for i in districts[j]:
        
        # What is its GEOID?
        geoID = G.nodes[i]["GEOID20"]
        
        # Need to find this GEOID in the dataframe
        for u in G.nodes:
            if geoID == df['GEOID20'][u]: # Found it
                assignment[u] = j # Node u from the dataframe should be assigned to district j

# Now add the assignments to a column of the dataframe and map it
df['assignment'] = assignment
my_fig = df.plot(column='assignment').get_figure()


# In[ ]:




