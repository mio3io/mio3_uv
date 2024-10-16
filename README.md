# Mio3 UV

A UV editing support addon I'm creating to make UV unwrapping more enjoyable. It includes features particularly suited for character modeling.

To preview all the features currently implemented, please refer to the documentation page.

Document [English](https://addon.mio3io.com/#/en/mio3uv/) / [Japanese](https://addon.mio3io.com/#/ja/mio3uv/)

## Install

[Blender Extensions](https://extensions.blender.org/add-ons/mio3-uv/)

## Location

UV Image Editor > Sidebar > Mio3

## Features

### Unwrap

-   **Unwrap**: Unwrap while maintaining the original position, size, and angle as much as possible
-   **Straight**: Unwrap so that the selected edge loop becomes a straight line
-   **Gridify**: Unwrap so that the selected face becomes a rectangle. Can be used for quadrilateral meshes
-   **Rectify**: Unwrap so that the boundary becomes a rectangle
-   **Projection Unwrap**: Unwrap by projecting from an angle parallel to the normal of the face selected in the 3D view

### Align

-   **Align**: Align selected elements to the top, bottom, left, right, or XY center position
-   **Rotate Selected UVs**
-   **Flip Selected UVs**
-   **Align Vertical/Horizontal Edges Only**: Align edge loops only in vertical or horizontal directions
-   **Orient Edge**: Adjust the angle and position of the island so that the selected edge becomes vertical or horizontal
-   **Align Axis**: Adjust to be vertical to the X or Y axis
-   **Orient World**: Align the angle of the island to the Z axis
-   **Noemalize**: Normalize the size and position of selected UVs
-   **Align Seams**: Align UV coordinates with the same 3D vertex that are separated by seams

### Vertex Operations

-   **Relax**: Smooth selected vertices
-   **Adjust Edge Length**: Adjust length based on geometry/equalize length
-   **Circle**: Adjust to form a clean circle
-   **Offset Boundary**: Expand or shrink the boundary UVs of the island

### Island Operations

-   **Sort**: Sort islands based on coordinates in 3D space
-   **Stack**: Stack similar islands
-   **Copy & Paste UV Shape**: Copy and paste the shape while maintaining the original position
-   **Unify Shapes**: Align UV shapes while maintaining the original position
-   **Shuffle**: Randomly rearrange island positions. If two islands are selected, exchange their positions
-   **Average Island Scales**: Adjust size based on the mesh size in 3D space
-   **Unfoldify**: Automatically layout selected islands based on their spatial relationships in 3D space

### Island Arrangement

-   **Sort Grid**: Arrange islands by grouping and sorting
-   **Align Body Parts**: Identify body parts based on coordinates and align orientation and order for intuitive layout

### Symmetry

-   **Symmetry**: Symmetrize UVs based on 3D space symmetry
-   **Snap to Symmetry**: Snap to the closest symmetrical UV

### Selection

-   **Select One Direction**: Select UVs on one side based on coordinates in 3D space
-   **Mirror Selection**: Select symmetrical UVs based on coordinates in 3D space
-   **Similar**: Select similar islands
-   **Boundary**: Select island boundaries
-   **Select Vertical/Horizontal Edges Only**
-   **No Region**: Select UVs that do not have an area
-   **Inverted UV Faces**: Select inverted UVs

### Mark Seams

-   **Angle-Based Seams**
-   **Mark Seams on Selection Boundary**

### Display Support

-   Use an original checker map
-   Display padding lines
