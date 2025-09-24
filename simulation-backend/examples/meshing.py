"""
Creating a mesh from geometry using Gmsh
========================================

CHORAS uses Gmsh to create meshes. Gmsh provides a scripting language or serves
as an API to geometry creation tools to define geometries and mesh them.
This example assumes that the geometry has been defined and is provided in
a Gmsh ``*.geo`` file.

For more information on Gmsh, please refer to the `Gmsh documentation
<https://gmsh.info/doc/texinfo/gmsh.html#Gmsh-application-programming-interface>`_.

"""
# %%
import numpy as np
import matplotlib.pyplot as plt
import gmsh
import matplotlib.tri as mtri

# %%
# For Gmsh to work, it always needs to be initialized first.
gmsh.initialize()
# %%
# Subsequently, the geometry file can be imported using the following function.
# Note that the function does not return anything, but the geometry is
# imported into the Gmsh model.
gmsh.open("example_room.geo")
# %%

element_type = gmsh.model.mesh.getElementType("triangle", 1)
surface_group_tags = gmsh.model.getPhysicalGroups(dim=element_type)
surface_group_names = [
    gmsh.model.getPhysicalName(element_type, tag)
    for (element_type, tag) in surface_group_tags
]


gmsh.model.mesh.generate(2)

# %%
node_tags_all, coords_all, _ = gmsh.model.mesh.getNodes()
node_tags_group, _ = gmsh.model.mesh.getNodesForPhysicalGroup(
    element_type, 1)
coords = coords_all.reshape((len(node_tags_all), 3))


# %%
dim_tags = gmsh.model.getEntitiesForPhysicalName("ceiling")
dim, tag = dim_tags[0]

# %%
node_tags_all, coords_all, _ = gmsh.model.mesh.getNodes(element_type)
face_nodes = gmsh.model.mesh.getElementFaceNodes(element_type, 3, tag=tag)
faces = np.reshape(face_nodes, (len(face_nodes) // 3, 3))
# %%
face_nodes = np.sort(face_nodes)

tri_plotting = mtri.Triangulation(
    coords[:, 0],
    coords[:, 1],
    faces-1
)
# %%
ax = plt.axes()
ax.scatter(coords[faces-1, 0], coords[faces-1, 1], color="gray")
ax.triplot(tri_plotting, color="gray")

# %%
surface_group_tags = gmsh.model.getPhysicalGroups(dim=element_type)
surface_group_names = [
    gmsh.model.getPhysicalName(element_type, tag)
    for (element_type, tag) in surface_group_tags
]
