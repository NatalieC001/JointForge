"""
JointForge - Smart Cut with Auto Keys
======================================

Author: Natalie C
Blender Version: 4.2.1 LTS

Behavior:
    - PLANE object: Straight cut through entire model at plane location
    - CUSTOM SHAPE: Finds intersection boundary, creates plane from it, cuts ONLY that area
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


def create_plane_from_intersection(target_obj, cutter_obj):
    """
    Find where cutter intersects target,
    create a plane mesh from that intersection boundary
    Returns the plane object and its center/normal/rotation
    """
    # Store original transforms
    target_world_mat = target_obj.matrix_world.copy()
    cutter_world_mat = cutter_obj.matrix_world.copy()
    
    # Create temporary collection to keep things clean
    temp_collection = bpy.data.collections.new("TempIntersection")
    bpy.context.scene.collection.children.link(temp_collection)
    
    # Create temporary objects with applied transforms
    temp_target = bpy.data.objects.new("TempTarget", target_obj.data.copy())
    temp_collection.objects.link(temp_target)
    temp_target.matrix_world = target_world_mat
    
    temp_cutter = bpy.data.objects.new("TempCutter", cutter_obj.data.copy())
    temp_collection.objects.link(temp_cutter)
    temp_cutter.matrix_world = cutter_world_mat
    
    # Set active and apply boolean
    bpy.context.view_layer.objects.active = temp_target
    
    # Select the target for boolean operation
    bpy.ops.object.select_all(action='DESELECT')
    temp_target.select_set(True)
    
    mod = temp_target.modifiers.new(name="Intersect", type='BOOLEAN')
    mod.object = temp_cutter
    mod.operation = 'INTERSECT'
    mod.solver = 'EXACT'
    
    # Apply the modifier
    try:
        bpy.ops.object.modifier_apply(modifier=mod.name)
    except Exception as e:
        print(f"Boolean failed: {e}")
        # Cleanup
        bpy.data.objects.remove(temp_target, do_unlink=True)
        bpy.data.objects.remove(temp_cutter, do_unlink=True)
        bpy.data.collections.remove(temp_collection)
        return None, None, None, None
    
    # Check if we have geometry
    if len(temp_target.data.vertices) == 0:
        print("No intersection geometry found")
        bpy.data.objects.remove(temp_target, do_unlink=True)
        bpy.data.objects.remove(temp_cutter, do_unlink=True)
        bpy.data.collections.remove(temp_collection)
        return None, None, None, None
    
    # Find boundary edges using bmesh
    bm = bmesh.new()
    bm.from_mesh(temp_target.data)
    
    # Remove duplicate vertices first
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)
    
    boundary_verts = []
    for edge in bm.edges:
        if edge.is_boundary:
            for vert in edge.verts:
                # Convert to world space
                world_vert = temp_target.matrix_world @ vert.co
                boundary_verts.append(world_vert)
    
    bm.free()
    
    if len(boundary_verts) < 3:
        print(f"Found only {len(boundary_verts)} boundary vertices, need at least 3")
        bpy.data.objects.remove(temp_target, do_unlink=True)
        bpy.data.objects.remove(temp_cutter, do_unlink=True)
        bpy.data.collections.remove(temp_collection)
        return None, None, None, None
    
    # Remove duplicate boundary vertices
    unique_verts = []
    tolerance = 0.001
    for v in boundary_verts:
        duplicate = False
        for u in unique_verts:
            if (v - u).length < tolerance:
                duplicate = True
                break
        if not duplicate:
            unique_verts.append(v)
    
    if len(unique_verts) < 3:
        print(f"After removing duplicates, only {len(unique_verts)} vertices remain")
        bpy.data.objects.remove(temp_target, do_unlink=True)
        bpy.data.objects.remove(temp_cutter, do_unlink=True)
        bpy.data.collections.remove(temp_collection)
        return None, None, None, None
    
    # Calculate center
    center = Vector((0, 0, 0))
    for v in unique_verts:
        center += v
    center /= len(unique_verts)
    
    # Calculate plane normal using Newell's method for robustness
    normal = Vector((0, 0, 0))
    for i in range(len(unique_verts)):
        current = unique_verts[i]
        next_vert = unique_verts[(i + 1) % len(unique_verts)]
        normal.x += (current.y - next_vert.y) * (current.z + next_vert.z)
        normal.y += (current.z - next_vert.z) * (current.x + next_vert.x)
        normal.z += (current.x - next_vert.x) * (current.y + next_vert.y)
    normal.normalize()
    
    # Create plane mesh
    plane_mesh = bpy.data.meshes.new("CutPlane_Mesh")
    plane_obj = bpy.data.objects.new("CutPlane", plane_mesh)
    bpy.context.collection.objects.link(plane_obj)
    plane_obj.location = center
    
    # Sort vertices by angle around center for proper face creation
    def get_angle(v, center, normal):
        local_v = v - center
        # Create reference vectors on the plane
        if abs(normal.x) > 0.9:
            ref_vec = Vector((0, 1, 0))
        else:
            ref_vec = Vector((1, 0, 0))
        up = normal.cross(ref_vec).normalized()
        right = up.cross(normal).normalized()
        x = local_v.dot(right)
        y = local_v.dot(up)
        return np.arctan2(y, x)
    
    try:
        import numpy as np
        sorted_verts = sorted(unique_verts, key=lambda v: get_angle(v, center, normal))
    except:
        # Fallback if numpy not available
        sorted_verts = unique_verts
    
    # Build mesh using bmesh
    bm = bmesh.new()
    for v in sorted_verts:
        bm.verts.new(v - center)
    bm.verts.ensure_lookup_table()
    
    # Create face from vertices
    if len(bm.verts) >= 3:
        face_verts = [bm.verts[i] for i in range(len(bm.verts))]
        bm.faces.new(face_verts)
    
    # Update mesh
    bm.to_mesh(plane_mesh)
    bm.free()
    plane_mesh.update()
    
    # Align plane to normal
    z_axis = Vector((0, 0, 1))
    if normal.length > 0 and z_axis != normal:
        q = z_axis.rotation_difference(normal)
        rotation = q.to_euler()
        plane_obj.rotation_euler = rotation
    else:
        rotation = cutter_obj.rotation_euler
    
    # Clean up
    bpy.data.objects.remove(temp_target, do_unlink=True)
    bpy.data.objects.remove(temp_cutter, do_unlink=True)
    bpy.data.collections.remove(temp_collection)
    
    return plane_obj, center, normal, rotation


class JOINTFORGE_OT_GenerateJoints(bpy.types.Operator):
    bl_idname = "object.jointforge_generate"
    bl_label = "Generate Joints"
    bl_description = "Smart cut: Plane=straight cut, Shape=intersection cut"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        target_mesh = scene.jointforge_target
        cutter = scene.jointforge_cutter
        
        if not target_mesh or not cutter:
            self.report({'ERROR'}, "Select both the Target Mesh and Cutter")
            return {'CANCELLED'}
        
        # Key dimensions
        key_size = scene.jointforge_key_size / 1000.0
        key_depth = scene.jointforge_key_depth / 1000.0
        gap = scene.jointforge_gap / 1000.0
        peg_part = scene.jointforge_peg_assignment
        
        # Check if cutter is a plane
        is_plane = "plane" in cutter.name.lower()
        
        if is_plane:
            # Use plane directly
            plane_co = cutter.location
            plane_no = cutter.matrix_world.to_quaternion() @ Vector((0, 0, 1))
            plane_no.normalize()
            plane_rot = cutter.rotation_euler
            temp_plane_obj = None
        else:
            # Create plane from intersection
            temp_plane_obj, plane_co, plane_no, plane_rot = create_plane_from_intersection(target_mesh, cutter)
            
            if not temp_plane_obj:
                self.report({'ERROR'}, "Could not find intersection. Make sure the shape clearly intersects the model!")
                return {'CANCELLED'}
        
        # Create collection for parts
        collection_name = f"{target_mesh.name}_Parts"
        if collection_name in bpy.data.collections:
            parts_collection = bpy.data.collections[collection_name]
        else:
            parts_collection = bpy.data.collections.new(collection_name)
            context.scene.collection.children.link(parts_collection)
        
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
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=plane_co, rotation=plane_rot)
        master_key = context.active_object
        master_key.name = "TEMP_MASTER_KEY"
        master_key.scale = (key_size, key_size, key_depth)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        
        # Position key correctly based on which part gets the peg
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
        
        # Hole cutter (scaled for gap)
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
        
        if temp_plane_obj:
            bpy.data.objects.remove(temp_plane_obj, do_unlink=True)
        
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
        
        if is_plane:
            self.report({'INFO'}, f"Straight cut made with plane! Key at plane center. Tolerance: {gap*1000:.1f}mm")
        else:
            self.report({'INFO'}, f"Intersection cut made! Key at intersection center. Tolerance: {gap*1000:.1f}mm")
        
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
        box.label(text="2. Select Cutter (plane OR any shape)")
        box.label(text="3. Click Generate Joints")
        
        layout.separator()
        
        box = layout.box()
        box.label(text="CUTTER BEHAVIOR:")
        box.label(text="• PLANE → Straight cut through model")
        box.label(text="• SHAPE → Cut ONLY where it intersects")
        
        layout.separator()
        
        layout.prop(scene, "jointforge_target", text="Target Mesh")
        layout.prop(scene, "jointforge_cutter", text="Cutter")
        
        layout.separator()
        
        box = layout.box()
        box.label(text="KEY SETTINGS:")
        box.prop(scene, "jointforge_key_size", text="Size (mm)")
        box.prop(scene, "jointforge_key_depth", text="Depth (mm)")
        box.prop(scene, "jointforge_gap", text="Gap (mm)")
        
        layout.separator()
        
        box = layout.box()
        box.label(text="PEG GOES ON:")
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
    bpy.types.Scene.jointforge_peg_assignment = bpy.props.EnumProperty(
        items=[('TOP', "Top Part", ""), ('BOTTOM', "Bottom Part", "")],
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
    del bpy.types.Scene.jointforge_peg_assignment

if __name__ == "__main__":
    register()
