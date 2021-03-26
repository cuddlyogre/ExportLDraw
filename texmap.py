import bpy
import os
import uuid


class TexMap:
    texmaps = {}

    @classmethod
    def reset_caches(cls):
        cls.texmaps.clear()

    def __init__(self, options):
        self.id = str(uuid.uuid4())
        self.method = options["method"]
        self.parameters = options["parameters"]
        self.texture = options["texture"]
        self.glossmap = options["glossmap"]

    def map_planar(self):
        a = self.parameters[0]
        b = self.parameters[1]
        c = self.parameters[2]

        ab = b - a
        bc = c - b
        ac = c - a

        texmap_cross = (ab).cross(ac)
        texmap_normal = texmap_cross / texmap_cross.length

        p1_length = ab.length
        p1_normal = ab / ab.length

        p2_length = ac.length
        p2_normal = ac / ac.length

        obj = bpy.data.objects['standard_16_rd_as_alt_ss_13710g.dat']
        mesh = obj.data

        name = 'uv'
        if name in mesh.uv_layers:
            uv = mesh.uv_layers[name]
            mesh.uv_layers.remove(layer=uv)
        if name not in mesh.uv_layers:
            mesh.uv_layers.new(name=name)
        uv_layer = mesh.uv_layers[name]

        # norm = [float(i)/max(raw) for i in raw]
        # m = max(raw); norm = [float(i)/m for i in raw]
        # https://blenderartists.org/t/i-want-to-get-a-selected-uv-vertex-index/598023/2
        vert_uv_map = {}
        for polygon in mesh.polygons:
            for li in polygon.loop_indices:
                vi = mesh.loops[li].vertex_index
                uv = uv_layer.data[li]
                vert_uv_map.setdefault(vi, []).append(uv)
                print(vi)

        max_du = 0
        max_dv = 0

        uv = {}
        print("")
        for index, uvs in vert_uv_map.items():
            p = mesh.vertices[index].co
            du = abs(p1_normal.dot(p - a)) / p1_length
            dv = abs(p2_normal.dot(p - c)) / p2_length
            distance = [du, dv]
            uv[index] = distance
            for u in uvs:
                u.uv = distance
            if du > max_du:
                max_du = du
            if dv > max_dv:
                max_dv = dv

        print(max_du)
        print(max_dv)
        for index, uvs in vert_uv_map.items():
            distance = uv[index]
            u = distance[0] / max_du
            v = distance[1] / max_dv

            print([u, v])
            for uu in uvs:
                uu.uv = [u, v]

        print("")
        print("")

        # raise KeyboardInterrupt()
        if name in mesh.materials:
            material = mesh.materials[name]
            mesh.materials.pop(index=list(mesh.materials).index(material))

        if name in bpy.data.materials:
            material = bpy.data.materials[name]
            bpy.data.materials.remove(material)

        if name not in bpy.data.materials:
            material = bpy.data.materials.new(name)
            material.use_nodes = True
        material = bpy.data.materials[name]

        nodes = material.node_tree.nodes
        links = material.node_tree.links
        nodes.clear()

        tex_image = nodes.new("ShaderNodeTexImage")
        tex_image.location = -300.0, 100.0
        tex_image.interpolation = "Closest"
        tex_image.extension = "CLIP"

        image_name = "13710g.png"
        image_path = os.path.join("d:\\ldraw", "unofficial", "parts", "textures", image_name)

        image_name = "19204p01.png"
        image_path = os.path.join("d:\\ldraw", "parts", "textures", image_name)

        if image_name not in bpy.data.images:
            bpy.data.images.load(image_path)
        tex_image.image = bpy.data.images[image_name]

        reroute = nodes.new("NodeReroute")
        reroute.name = "LDRAW MATERIAL POSITION"
        reroute.location = 0.0, 0.0

        principled = nodes.new("ShaderNodeBsdfPrincipled")
        principled.name = "REPLACE WITH LDRAW MATERIAL"
        principled.location = 0.0, -220.0
        diff_color = (0.346704, 0.004025, 1.0) + (1.0,)
        principled.inputs["Base Color"].default_value = diff_color
        principled.inputs["Metallic"].default_value = 0.0
        principled.inputs["Roughness"].default_value = 0.1
        principled.inputs["Clearcoat"].default_value = 0.0
        principled.inputs["Clearcoat Roughness"].default_value = 0.0
        principled.inputs["IOR"].default_value = 1.45
        principled.inputs["Transmission"].default_value = 0.0

        mix = nodes.new("ShaderNodeMixShader")
        mix.location = 100.0, 180.0

        out = nodes.new("ShaderNodeOutputMaterial")
        out.location = 200.0, 0.0

        links.new(tex_image.outputs["Color"], mix.inputs[2])
        links.new(tex_image.outputs["Alpha"], mix.inputs[0])
        links.new(principled.outputs["BSDF"], mix.inputs[1])
        links.new(mix.outputs["Shader"], out.inputs[0])

        # pmesh.materials.append(material)
        mesh.materials.append(material)
        # obj.active_material = material
        # obj.active_material_index = list(mesh.materials).index(material)

        # obj.active_material = mat
        # obj.active_material_index
        # obj.material_slots[idx].material = mat
