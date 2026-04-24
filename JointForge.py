
"""
JointForge - Precision Keyed Joint Generator for 3D Printing
=============================================================

Author: Natalie C
Blender Version: 4.2.1 LTS (should work with 4.0+)
Created: 2026

Description:
    This add-on creates precise keyed joints for splitting and reassembling 3D models.
    Perfect for printing models that exceed your printer's build volume.

Installation Instructions:
    ========================
    METHOD 1 - Text Editor (Quick Install):
        1. Open Blender        2. Go to Scripting workspace
        3. Click "New" in the Text Editor
        4. Paste this entire script
        5. Click "Run Script" button (play icon)
        6. The add-on is now registered!
        7. Find "JointForge" in the 3D Viewport sidebar (press N key)
    
    METHOD 2 - Permanent Install:
        1. Save this file as "jointforge.py"
        2. Edit → Preferences → Add-ons → Install
        3. Select the file and enable "Mesh: JointForge"
        4. Find "JointForge" in the 3D Viewport sidebar (press N key)
    
    Once installed, you'll see "JointForge" in the sidebar (N key) under the main tabs.

How to Use:
    1. Select your mesh (the model to split)
    2. Select a plane object (defines where to cut)
    3. Adjust key dimensions (mm)
    4. Choose which part gets the peg
    5. Click "Generate Joints"

Features:
    - Creates male/female keyed joints for 3D printed assembly
    - Adjustable key size, depth, and fit tolerance
    - Choose which part receives the peg vs notch
    - Original mesh preserved in hidden state
    - Parts organized in dedicated collection

Compatibility:
    Tested on Blender 4.2.1 LTS
    Should work on Blender 4.0 and above
"""





import bpy
import bmesh
from mathutils import Vector

# -------------------------------------------------------------------
# Main operator
# -------------------------------------------------------------------
class BIRD_SLICER_OT_Execute(bpy.types.Operator):
    bl_idname = "object.run_bird_slicer"
    bl_label = "Generate Keyed Joint"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        bird = scene.target_model
        plane = scene.slicer_plane
        
        if not bird or not plane:
            self.report({'ERROR'}, "Select both the Bird and Slicer Plane")
            return {'CANCELLED'}
        
        # Get plane data
        plane_co = plane.location
        plane_no = plane.matrix_world.to_quaternion() @ Vector((0, 0, 1))
        plane_no.normalize()
        plane_rot = plane.rotation_euler
        
        # Key dimensions in meters
        key_size = scene.key_size / 1000.0
        key_depth = scene.key_depth / 1000.0
        gap = scene.fit_gap / 1000.0
        
        # Which part gets what
        peg_part = scene.peg_assignment  # 'TOP' or 'BOTTOM'
        
        # Create a new collection for the parts
        collection_name = f"{bird.name}_Parts"
        if collection_name in bpy.data.collections:
            parts_collection = bpy.data.collections[collection_name]
        else:
            parts_collection = bpy.data.collections.new(collection_name)
            context.scene.collection.children.link(parts_collection)
        
        # -----------------------------------------------------------
        # Create TOP part (keep everything ABOVE the plane)
        # -----------------------------------------------------------
        top_obj = bird.copy()
        top_obj.data = bird.data.copy()
        top_obj.name = f"{bird.name}_TOP"
        top_obj.location = bird.location
        parts_collection.objects.link(top_obj)
        
        # Slice top using bisect (keep upper part)
        bm = bmesh.new()
        bm.from_mesh(top_obj.data)
        
        inv_mat = top_obj.matrix_world.inverted()
        local_co = inv_mat @ plane_co
        local_no = (inv_mat.to_3x3() @ plane_no).normalized()
        
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=local_co, plane_no=local_no, dist=0.0001, clear_inner=False, clear_outer=True)
        
        bm.to_mesh(top_obj.data)
        bm.free()
        
        # -----------------------------------------------------------
        # Create BOTTOM part (keep everything BELOW the plane)
        # -----------------------------------------------------------
        bottom_obj = bird.copy()
        bottom_obj.data = bird.data.copy()
        bottom_obj.name = f"{bird.name}_BOTTOM"
        bottom_obj.location = bird.location
        parts_collection.objects.link(bottom_obj)
        
        # Slice bottom using bisect (keep lower part)
        bm = bmesh.new()
        bm.from_mesh(bottom_obj.data)
        
        inv_mat = bottom_obj.matrix_world.inverted()
        local_co = inv_mat @ plane_co
        local_no = (inv_mat.to_3x3() @ plane_no).normalized()
        
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=local_co, plane_no=local_no, dist=0.0001, clear_inner=True, clear_outer=False)
        
        bm.to_mesh(bottom_obj.data)
        bm.free()
        
        # -----------------------------------------------------------
        # Fill the cut faces on both parts
        # -----------------------------------------------------------
        for obj in [top_obj, bottom_obj]:
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            
            # Find boundary edges to fill
            boundary_edges = [e for e in bm.edges if e.is_boundary]
            if boundary_edges:
                bmesh.ops.edgeloop_fill(bm, edges=boundary_edges)
            
            bm.to_mesh(obj.data)
            bm.free()
        
        # -----------------------------------------------------------
        # Create the MASTER KEY (exact size, centered on the cut plane)
        # -----------------------------------------------------------
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=plane_co, rotation=plane_rot)
        master_key = context.active_object
        master_key.name = "TEMP_MASTER_KEY"
        master_key.scale = (key_size, key_size, key_depth)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        
        # -----------------------------------------------------------
        # Duplicate master key for the peg (additive)
        # -----------------------------------------------------------
        peg = master_key.copy()
        peg.data = master_key.data.copy()
        peg.name = "TEMP_PEG"
        peg.location = plane_co
        context.collection.objects.link(peg)
        
        # -----------------------------------------------------------
        # Duplicate master key and scale it up for the hole (subtractive)
        # This creates the gap clearance
        # -----------------------------------------------------------
        hole_cutter = master_key.copy()
        hole_cutter.data = master_key.data.copy()
        hole_cutter.name = "TEMP_HOLE_CUTTER"
        hole_cutter.location = plane_co
        hole_cutter.scale = (1 + (gap/key_size), 1 + (gap/key_size), 1 + (gap/key_depth))
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        context.collection.objects.link(hole_cutter)
        
        # -----------------------------------------------------------
        # Apply based on user choice
        # -----------------------------------------------------------
        if peg_part == 'TOP':
            # TOP gets the peg (additive), BOTTOM gets the hole (subtractive)
            bpy.context.view_layer.objects.active = top_obj
            mod_peg = top_obj.modifiers.new(name="AddPeg", type='BOOLEAN')
            mod_peg.object = peg
            mod_peg.operation = 'UNION'
            mod_peg.solver = 'EXACT'
            bpy.ops.object.modifier_apply(modifier=mod_peg.name)
            
            bpy.context.view_layer.objects.active = bottom_obj
            mod_hole = bottom_obj.modifiers.new(name="CarveHole", type='BOOLEAN')
            mod_hole.object = hole_cutter
            mod_hole.operation = 'DIFFERENCE'
            mod_hole.solver = 'EXACT'
            bpy.ops.object.modifier_apply(modifier=mod_hole.name)
            
            self.report({'INFO'}, f"TOP part gets PEG, BOTTOM part gets HOLE")
            
        else:  # peg_part == 'BOTTOM'
            # BOTTOM gets the peg (additive), TOP gets the hole (subtractive)
            bpy.context.view_layer.objects.active = bottom_obj
            mod_peg = bottom_obj.modifiers.new(name="AddPeg", type='BOOLEAN')
            mod_peg.object = peg
            mod_peg.operation = 'UNION'
            mod_peg.solver = 'EXACT'
            bpy.ops.object.modifier_apply(modifier=mod_peg.name)
            
            bpy.context.view_layer.objects.active = top_obj
            mod_hole = top_obj.modifiers.new(name="CarveHole", type='BOOLEAN')
            mod_hole.object = hole_cutter
            mod_hole.operation = 'DIFFERENCE'
            mod_hole.solver = 'EXACT'
            bpy.ops.object.modifier_apply(modifier=mod_hole.name)
            
            self.report({'INFO'}, f"BOTTOM part gets PEG, TOP part gets HOLE")
        
        # -----------------------------------------------------------
        # Clean up temporary objects
        # -----------------------------------------------------------
        bpy.data.objects.remove(master_key, do_unlink=True)
        bpy.data.objects.remove(peg, do_unlink=True)
        bpy.data.objects.remove(hole_cutter, do_unlink=True)
        
        # -----------------------------------------------------------
        # Finalize
        # -----------------------------------------------------------
        bird.hide_set(True)
        
        # Select the new parts
        bpy.ops.object.select_all(action='DESELECT')
        top_obj.select_set(True)
        bottom_obj.select_set(True)
        context.view_layer.objects.active = top_obj
        
        return {'FINISHED'}


# -------------------------------------------------------------------
# UI Panel
# -------------------------------------------------------------------
class BIRD_SLICER_PT_Panel(bpy.types.Panel):
    bl_label = "Bird Slicer"
    bl_idname = "BIRD_SLICER_PT_Panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Bird Slicer"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        layout.prop(scene, "target_model", text="Bird")
        layout.prop(scene, "slicer_plane", text="Slicer Plane")
        layout.separator()
        layout.prop(scene, "key_size", text="Key Size (mm)")
        layout.prop(scene, "key_depth", text="Key Depth (mm)")
        layout.prop(scene, "fit_gap", text="Fit Gap (mm)")
        layout.separator()
        layout.label(text="Peg Assignment:")
        layout.prop(scene, "peg_assignment", text="")
        layout.separator()
        layout.label(text=f"Note: Hole will be {scene.key_size + scene.fit_gap}mm")
        layout.separator()
        layout.operator("object.run_bird_slicer", text="Generate Joints")


# -------------------------------------------------------------------
# Registration
# -------------------------------------------------------------------
classes = (BIRD_SLICER_OT_Execute, BIRD_SLICER_PT_Panel)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.target_model = bpy.props.PointerProperty(type=bpy.types.Object)
    bpy.types.Scene.slicer_plane = bpy.props.PointerProperty(type=bpy.types.Object)
    bpy.types.Scene.key_size = bpy.props.FloatProperty(default=5.0, min=0.1)
    bpy.types.Scene.key_depth = bpy.props.FloatProperty(default=4.0, min=0.1)
    bpy.types.Scene.fit_gap = bpy.props.FloatProperty(default=0.2, min=0.0)
    bpy.types.Scene.peg_assignment = bpy.props.EnumProperty(
        name="Peg Assignment",
        description="Which part gets the peg (additive) and which gets the hole (subtractive)",
        items=[
            ('TOP', "Peg on TOP", "Top part gets the peg, bottom part gets the hole"),
            ('BOTTOM', "Peg on BOTTOM", "Bottom part gets the peg, top part gets the hole")
        ],
        default='BOTTOM'
    )

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    
    del bpy.types.Scene.target_model
    del bpy.types.Scene.slicer_plane
    del bpy.types.Scene.key_size
    del bpy.types.Scene.key_depth
    del bpy.types.Scene.fit_gap
    del bpy.types.Scene.peg_assignment

if __name__ == "__main__":
    register()
