"""
JointForge - Smart Cut with Auto Keys
======================================

Author: Natalie C
Blender Version: 4.2.1 LTS

Behavior:
    - PLANE object: Straight cut through entire model at plane location
    - 3D SHAPE (cube, sphere, etc.): Carves out that shape from the model
    - KEY: Optional for shapes, always added for planes
"""

bl_info = {
    "name": "JointForge",
    "author": "Natalie C",
    "version": (5, 1, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > JointForge",
    "category": "Mesh",
}

import bpy
import bmesh
from mathutils import Vector


class JOINTFORGE_OT_GenerateJoints(bpy.types.Operator):
    bl_idname = "object.jointforge_generate"
    bl_label = "Generate Joints"
    bl_description = "Smart cut: Plane=straight cut, 3D Shape=carves out shape"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        target_mesh = scene.jointforge_target
        cutter = scene.jointforge_cutter
        
        if not target_mesh or not cutter:
            self.report({'ERROR'}, "Select both the Target Mesh and Cutter")
            return {'CANCELLED'}
        
        # Key settings - user sees mm, Blender uses meters
        key_size_mm = scene.jointforge_key_size
        key_depth_mm = scene.jointforge_key_depth
        gap_mm = scene.jointforge_gap
        
        # Convert mm to meters for Blender
        key_size = key_size_mm / 1000.0
        key_depth = key_depth_mm / 1000.0
        gap = gap_mm / 1000.0
        
        peg_part = scene.jointforge_peg_assignment
        add_key_to_shape = scene.jointforge_add_key_to_shape
        
        # Check if cutter is a plane (name contains "plane")
        is_plane = "plane" in cutter.name.lower()
        
        # Create collection for parts
        collection_name = f"{target_mesh.name}_Parts"
        if collection_name in bpy.data.collections:
            parts_collection = bpy.data.collections[collection_name]
        else:
            parts_collection = bpy.data.collections.new(collection_name)
            context.scene.collection.children.link(parts_collection)
        
        if is_plane:
            # ========== PLANE: Straight bisect cut through entire model ==========
            plane_co = cutter.location
            plane_no = cutter.matrix_world.to_quaternion() @ Vector((0, 0, 1))
            plane_no.normalize()
            plane_rot = cutter.rotation_euler
            
            # Create TOP part
            top_obj = target_mesh.copy()
            top_obj.data = target_mesh.data.copy()
            top_obj.name = f"{target_mesh.name}_TOP"
            top_obj.location = target_mesh.location
            parts_collection.objects.link(top_obj)
            
            bm = bmesh.new()
            bm.from_mesh(top_obj.data)
            inv_mat = top_obj.matrix_world.inverted()
            local_co = inv_mat @ plane_co
            local_no = (inv_mat.to_3x3() @ plane_no).normalized()
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=local_co, plane_no=local_no,
                                   dist=0.0001, clear_inner=False, clear_outer=True)
            bm.to_mesh(top_obj.data)
            bm.free()
            
            # Create BOTTOM part
            bottom_obj = target_mesh.copy()
            bottom_obj.data = target_mesh.data.copy()
            bottom_obj.name = f"{target_mesh.name}_BOTTOM"
            bottom_obj.location = target_mesh.location
            parts_collection.objects.link(bottom_obj)
            
            bm = bmesh.new()
            bm.from_mesh(bottom_obj.data)
            inv_mat = bottom_obj.matrix_world.inverted()
            local_co = inv_mat @ plane_co
            local_no = (inv_mat.to_3x3() @ plane_no).normalized()
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=local_co, plane_no=local_no,
                                   dist=0.0001, clear_inner=True, clear_outer=False)
            bm.to_mesh(bottom_obj.data)
            bm.free()
            
            # Fill cut faces
            for obj in [top_obj, bottom_obj]:
                bm = bmesh.new()
                bm.from_mesh(obj.data)
                boundary_edges = [e for e in bm.edges if e.is_boundary]
                if boundary_edges:
                    try:
                        bmesh.ops.edgeloop_fill(bm, edges=boundary_edges)
                    except:
                        pass
                bm.to_mesh(obj.data)
                bm.free()
            
            # Create key at plane center
            bpy.ops.mesh.primitive_cube_add(size=key_size, location=plane_co, rotation=plane_rot)
            master_key = context.active_object
            master_key.name = "TEMP_MASTER_KEY"
            master_key.scale = (1, 1, key_depth / key_size if key_size > 0 else 1)
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            
            # Position key
            if peg_part == 'TOP':
                master_key.location = plane_co + (plane_no * (key_depth / 2))
            else:
                master_key.location = plane_co - (plane_no * (key_depth / 2))
            
            # Peg
            peg = master_key.copy()
            peg.data = master_key.data.copy()
            peg.name = "TEMP_PEG"
            peg.location = master_key.location
            context.collection.objects.link(peg)
            
            # Hole cutter
            hole_cutter = master_key.copy()
            hole_cutter.data = master_key.data.copy()
            hole_cutter.name = "TEMP_HOLE_CUTTER"
            hole_cutter.location = master_key.location
            scale_factor_x = 1 + (gap/key_size) if key_size > 0 else 1
            scale_factor_y = 1 + (gap/key_size) if key_size > 0 else 1
            scale_factor_z = 1 + (gap/key_depth) if key_depth > 0 else 1
            hole_cutter.scale = (scale_factor_x, scale_factor_y, scale_factor_z)
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            context.collection.objects.link(hole_cutter)
            
            # Apply to parts
            if peg_part == 'TOP':
                context.view_layer.objects.active = top_obj
                mod_peg = top_obj.modifiers.new(name="AddPeg", type='BOOLEAN')
                mod_peg.object = peg
                mod_peg.operation = 'UNION'
                mod_peg.solver = 'EXACT'
                bpy.ops.object.modifier_apply(modifier=mod_peg.name)
                
                context.view_layer.objects.active = bottom_obj
                mod_hole = bottom_obj.modifiers.new(name="CarveHole", type='BOOLEAN')
                mod_hole.object = hole_cutter
                mod_hole.operation = 'DIFFERENCE'
                mod_hole.solver = 'EXACT'
                bpy.ops.object.modifier_apply(modifier=mod_hole.name)
            else:
                context.view_layer.objects.active = bottom_obj
                mod_peg = bottom_obj.modifiers.new(name="AddPeg", type='BOOLEAN')
                mod_peg.object = peg
                mod_peg.operation = 'UNION'
                mod_peg.solver = 'EXACT'
                bpy.ops.object.modifier_apply(modifier=mod_peg.name)
                
                context.view_layer.objects.active = top_obj
                mod_hole = top_obj.modifiers.new(name="CarveHole", type='BOOLEAN')
                mod_hole.object = hole_cutter
                mod_hole.operation = 'DIFFERENCE'
                mod_hole.solver = 'EXACT'
                bpy.ops.object.modifier_apply(modifier=mod_hole.name)
            
            # Cleanup
            bpy.data.objects.remove(master_key, do_unlink=True)
            bpy.data.objects.remove(peg, do_unlink=True)
            bpy.data.objects.remove(hole_cutter, do_unlink=True)
            
            # Hide originals
            target_mesh.hide_set(True)
            cutter.hide_set(True)
            
            # Move to hidden collection
            hidden_collection = "JointForge_Originals"
            if hidden_collection not in bpy.data.collections:
                hidden_col = bpy.data.collections.new(hidden_collection)
                context.scene.collection.children.link(hidden_col)
            else:
                hidden_col = bpy.data.collections[hidden_collection]
            
            for obj in [target_mesh, cutter]:
                for col in obj.users_collection:
                    col.objects.unlink(obj)
                hidden_col.objects.link(obj)
            
            # Select new parts
            bpy.ops.object.select_all(action='DESELECT')
            top_obj.select_set(True)
            bottom_obj.select_set(True)
            context.view_layer.objects.active = top_obj
            
            self.report({'INFO'}, f"Plane cut complete! Tolerance: {gap_mm:.1f}mm")
            
        else:
            # ========== 3D SHAPE: Carve out using boolean ==========
            self.report({'INFO'}, f"3D Shape detected - carving out shape")
            
            # Make cutter visible for boolean
            cutter.hide_set(False)
            
            # Create OUTSIDE part (target minus the cutter shape) - the body with a hole
            outside_obj = target_mesh.copy()
            outside_obj.data = target_mesh.data.copy()
            outside_obj.name = f"{target_mesh.name}_OUTSIDE"
            outside_obj.location = target_mesh.location
            parts_collection.objects.link(outside_obj)
            
            context.view_layer.objects.active = outside_obj
            mod_outside = outside_obj.modifiers.new(name="SubtractShape", type='BOOLEAN')
            mod_outside.object = cutter
            mod_outside.operation = 'DIFFERENCE'
            mod_outside.solver = 'EXACT'
            
            try:
                bpy.ops.object.modifier_apply(modifier=mod_outside.name)
                self.report({'INFO'}, "Outside piece created successfully")
            except Exception as e:
                self.report({'ERROR'}, f"Boolean failed for outside: {str(e)}")
                bpy.data.objects.remove(outside_obj, do_unlink=True)
                cutter.hide_set(True)
                return {'CANCELLED'}
            
            # Create INSIDE part (target INTERSECT cutter) - the piece that gets cut out
            inside_obj = target_mesh.copy()
            inside_obj.data = target_mesh.data.copy()
            inside_obj.name = f"{target_mesh.name}_INSIDE"
            inside_obj.location = target_mesh.location
            parts_collection.objects.link(inside_obj)
            
            context.view_layer.objects.active = inside_obj
            mod_inside = inside_obj.modifiers.new(name="IntersectShape", type='BOOLEAN')
            mod_inside.object = cutter
            mod_inside.operation = 'INTERSECT'
            mod_inside.solver = 'EXACT'
            
            try:
                bpy.ops.object.modifier_apply(modifier=mod_inside.name)
                self.report({'INFO'}, "Inside piece created successfully")
            except Exception as e:
                self.report({'ERROR'}, f"Boolean failed for inside: {str(e)}")
                bpy.data.objects.remove(inside_obj, do_unlink=True)
                cutter.hide_set(True)
                return {'CANCELLED'}
            
            # Hide cutter
            cutter.hide_set(True)
            
            # Optionally add key based on peg assignment
            if add_key_to_shape:
                # 'BOTTOM' = key goes on INSIDE piece (the cutout)
                # 'TOP' = key goes on OUTSIDE piece (the main body)
                
                if peg_part == 'BOTTOM':
                    peg_piece = inside_obj
                    hole_piece = outside_obj
                    self.report({'INFO'}, "Adding key to INSIDE piece (cutout)")
                else:
                    peg_piece = outside_obj
                    hole_piece = inside_obj
                    self.report({'INFO'}, "Adding key to OUTSIDE piece (main body)")
                
                # Find the face on the peg piece that faces the other piece
                bm = bmesh.new()
                bm.from_mesh(peg_piece.data)
                
                # Transform vertices to world space
                world_mat = peg_piece.matrix_world
                for vert in bm.verts:
                    vert.co = world_mat @ vert.co
                
                # Find the interface face (closest to the other piece)
                # Calculate the center of the other piece's bounding box for reference
                other_world_mat = hole_piece.matrix_world
                other_center = Vector((0, 0, 0))
                for vert in hole_piece.data.vertices:
                    other_center += other_world_mat @ vert.co
                other_center /= len(hole_piece.data.vertices)
                
                # Find face with center closest to the other piece
                min_distance = 999999
                interface_face_center = None
                interface_face_normal = None
                
                for face in bm.faces:
                    center = Vector((0, 0, 0))
                    for vert in face.verts:
                        center += vert.co
                    center /= len(face.verts)
                    distance = (center - other_center).length
                    if distance < min_distance:
                        min_distance = distance
                        interface_face_center = center
                        interface_face_normal = face.normal.copy()
                
                bm.free()
                
                if interface_face_center and interface_face_normal:
                    # Calculate rotation to align Z axis with face normal
                    z_axis = Vector((0, 0, 1))
                    if interface_face_normal.length > 0 and z_axis != interface_face_normal:
                        q = z_axis.rotation_difference(interface_face_normal)
                        key_rotation = q.to_euler()
                    else:
                        key_rotation = cutter.rotation_euler
                    
                    # Create key at the interface face center
                    bpy.ops.mesh.primitive_cube_add(size=key_size, location=interface_face_center, rotation=key_rotation)
                    master_key = context.active_object
                    master_key.name = "TEMP_MASTER_KEY"
                    master_key.scale = (1, 1, key_depth / key_size if key_size > 0 else 1)
                    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
                    
                    # Position key half depth extending into the piece
                    master_key.location = interface_face_center + (interface_face_normal * (key_depth / 2))
                    
                    # Create peg
                    peg = master_key.copy()
                    peg.data = master_key.data.copy()
                    peg.name = "TEMP_PEG"
                    peg.location = master_key.location
                    context.collection.objects.link(peg)
                    
                    # Add peg to the peg piece
                    context.view_layer.objects.active = peg_piece
                    mod_peg = peg_piece.modifiers.new(name="AddPeg", type='BOOLEAN')
                    mod_peg.object = peg
                    mod_peg.operation = 'UNION'
                    mod_peg.solver = 'EXACT'
                    bpy.ops.object.modifier_apply(modifier=mod_peg.name)
                    
                    # Create hole cutter (scaled for gap)
                    hole_cutter = master_key.copy()
                    hole_cutter.data = master_key.data.copy()
                    hole_cutter.name = "TEMP_HOLE_CUTTER"
                    hole_cutter.location = master_key.location
                    scale_factor_x = 1 + (gap/key_size) if key_size > 0 else 1
                    scale_factor_y = 1 + (gap/key_size) if key_size > 0 else 1
                    scale_factor_z = 1 + (gap/key_depth) if key_depth > 0 else 1
                    hole_cutter.scale = (scale_factor_x, scale_factor_y, scale_factor_z)
                    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
                    context.collection.objects.link(hole_cutter)
                    
                    # Add matching hole to the other piece
                    context.view_layer.objects.active = hole_piece
                    mod_hole = hole_piece.modifiers.new(name="CarveHole", type='BOOLEAN')
                    mod_hole.object = hole_cutter
                    mod_hole.operation = 'DIFFERENCE'
                    mod_hole.solver = 'EXACT'
                    bpy.ops.object.modifier_apply(modifier=mod_hole.name)
                    
                    # Cleanup
                    bpy.data.objects.remove(master_key, do_unlink=True)
                    bpy.data.objects.remove(peg, do_unlink=True)
                    bpy.data.objects.remove(hole_cutter, do_unlink=True)
                else:
                    self.report({'WARNING'}, "Could not find interface face for key placement")
            
            # Hide original target
            target_mesh.hide_set(True)
            
            # Move originals to hidden collection
            hidden_collection = "JointForge_Originals"
            if hidden_collection not in bpy.data.collections:
                hidden_col = bpy.data.collections.new(hidden_collection)
                context.scene.collection.children.link(hidden_col)
            else:
                hidden_col = bpy.data.collections[hidden_collection]
            
            for obj in [target_mesh, cutter]:
                for col in obj.users_collection:
                    col.objects.unlink(obj)
                hidden_col.objects.link(obj)
            
            # Select both pieces
            bpy.ops.object.select_all(action='DESELECT')
            outside_obj.select_set(True)
            inside_obj.select_set(True)
            context.view_layer.objects.active = outside_obj
            
            if add_key_to_shape:
                self.report({'INFO'}, f"Shape carved out with key added! Tolerance: {gap_mm:.1f}mm")
            else:
                self.report({'INFO'}, "Shape carved out successfully! Outside and inside pieces created.")
        
        return {'FINISHED'}


class JOINTFORGE_PT_Panel(bpy.types.Panel):
    bl_label = "JointForge"
    bl_idname = "JOINTFORGE_PT_Panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "JointForge"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        box = layout.box()
        box.label(text="HOW TO USE:")
        box.label(text="1. Select Target Mesh (your model)")
        box.label(text="2. Select Cutter (plane OR any 3D shape)")
        box.label(text="3. Click Generate Joints")
        
        layout.separator()
        
        box = layout.box()
        box.label(text="CUTTER BEHAVIOR:")
        box.label(text="PLANE (name contains 'plane')")
        box.label(text="  → Splits model into two parts")
        box.label(text="  → Key placed ON the cut plane")
        box.label(text="")
        box.label(text="3D SHAPE (cube, sphere, wedge, etc.)")
        box.label(text="  → Creates OUTSIDE (body with hole)")
        box.label(text="  → Creates INSIDE (cut-out piece)")
        box.label(text="  → Optional key added based on PEG setting")
        
        layout.separator()
        
        layout.prop(scene, "jointforge_target", text="Target Mesh")
        layout.prop(scene, "jointforge_cutter", text="Cutter")
        
        layout.separator()
        
        box = layout.box()
        box.label(text="KEY SETTINGS:")
        box.prop(scene, "jointforge_key_size", text="Size (mm)")
        box.prop(scene, "jointforge_key_depth", text="Depth (mm)")
        box.prop(scene, "jointforge_gap", text="Gap (mm)")
        box.prop(scene, "jointforge_add_key_to_shape", text="Add key to shape cut")
        
        layout.separator()
        
        box = layout.box()
        box.label(text="PEG GOES ON:")
        box.label(text="  BOTTOM = cutout piece (INSIDE)")
        box.label(text="  TOP = main body (OUTSIDE)")
        box.prop(scene, "jointforge_peg_assignment", expand=True)
        
        layout.separator()
        
        layout.operator("object.jointforge_generate", text="GENERATE JOINTS", icon='MOD_BOOLEAN')


classes = (JOINTFORGE_OT_GenerateJoints, JOINTFORGE_PT_Panel)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.jointforge_target = bpy.props.PointerProperty(type=bpy.types.Object)
    bpy.types.Scene.jointforge_cutter = bpy.props.PointerProperty(type=bpy.types.Object)
    bpy.types.Scene.jointforge_key_size = bpy.props.FloatProperty(default=5.0, min=0.1)
    bpy.types.Scene.jointforge_key_depth = bpy.props.FloatProperty(default=4.0, min=0.1)
    bpy.types.Scene.jointforge_gap = bpy.props.FloatProperty(default=0.2, min=0.0)
    bpy.types.Scene.jointforge_add_key_to_shape = bpy.props.BoolProperty(default=False, name="Add key to shape cut")
    bpy.types.Scene.jointforge_peg_assignment = bpy.props.EnumProperty(
        items=[('TOP', "Top Part (OUTSIDE)", ""), ('BOTTOM', "Bottom Part (INSIDE)", "")],
        default='BOTTOM'
    )

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    
    del bpy.types.Scene.jointforge_target
    del bpy.types.Scene.jointforge_cutter
    del bpy.types.Scene.jointforge_key_size
    del bpy.types.Scene.jointforge_key_depth
    del bpy.types.Scene.jointforge_gap
    del bpy.types.Scene.jointforge_add_key_to_shape
    del bpy.types.Scene.jointforge_peg_assignment

if __name__ == "__main__":
    register()
