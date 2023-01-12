'''
Demonstrates how to programmatically generate a textured quad using the omni.ui.DynamicTextureProvider API.
This is contrived example that reads the image from the local filesystem (cat.jpg). You can imagine
sourcing the image bytes from a network request instead.

Resources:
- https://docs.omniverse.nvidia.com/kit/docs/omni.ui/latest/omni.ui/omni.ui.ByteImageProvider.html
- See the full list of omni.ui.TextureFormat variants at .\app\kit\extscore\omni.gpu_foundation\omni\gpu_foundation_factory\_gpu_foundation_factory.pyi

TODO(jshrake):
- [ ] Currently the dynamic texture name only works with the OmniPBR.mdl material. Need to understand why it doesn't work
    with other materials, such as UsdPreviewSurface.
- [ ] Test instantiating and using the DynamicTextureProvider in a separate thread
'''

from typing import Tuple, Union
import pathlib

import omni
import omni.ui as ui
from PIL import Image
from pxr import Kind, Sdf, Usd, UsdGeom, UsdShade

def create_textured_plane_prim(stage: Usd.Stage, prim_path: str, texture_name: str) -> Usd.Prim:
    # This code is mostly copy pasted from https://graphics.pixar.com/usd/release/tut_simple_shading.html
    billboard = UsdGeom.Mesh.Define(stage, f"{prim_path}/Mesh")
    billboard.CreatePointsAttr([(-430, -145, 0), (430, -145, 0), (430, 145, 0), (-430, 145, 0)])
    billboard.CreateFaceVertexCountsAttr([4])
    billboard.CreateFaceVertexIndicesAttr([0,1,2,3])
    billboard.CreateExtentAttr([(-430, -145, 0), (430, 145, 0)])
    texCoords = UsdGeom.PrimvarsAPI(billboard).CreatePrimvar("st",
                                        Sdf.ValueTypeNames.TexCoord2fArray,
                                        UsdGeom.Tokens.varying)
    texCoords.Set([(0, 0), (1, 0), (1,1), (0, 1)])

    material_path = f"{prim_path}/Material"
    material = UsdShade.Material.Define(stage, material_path)
    shader: UsdShade.Shader = UsdShade.Shader.Define(stage, f"{material_path}/Shader")
    shader.SetSourceAsset("OmniPBR.mdl", "mdl")
    shader.SetSourceAssetSubIdentifier("OmniPBR", "mdl");
    shader.CreateIdAttr("OmniPBR")
    shader.CreateInput("diffuse_texture", Sdf.ValueTypeNames.Asset).Set(f"dynamic://{texture_name}")
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    billboard.GetPrim().ApplyAPI(UsdShade.MaterialBindingAPI)
    UsdShade.MaterialBindingAPI(billboard).Bind(material)
    return billboard

def create_dynamic_texture(texture_name: str, bytes: bytes, resolution: Tuple[int, int], format: ui.TextureFormat) -> ui.DynamicTextureProvider:
    # See https://docs.omniverse.nvidia.com/kit/docs/omni.ui/latest/omni.ui/omni.ui.ByteImageProvider.html#omni.ui.ByteImageProvider.set_bytes_data_from_gpu
    bytes_list = list(bytes)
    dtp = ui.DynamicTextureProvider(texture_name)
    dtp.set_bytes_data(bytes_list, list(resolution), format)
    return dtp

class DynamicTextureProviderExample(omni.ext.IExt):
    def on_startup(self, ext_id):
        self._texture: Union[None, ui.DynamicTextureProvider] = None
        self._window = ui.Window("Create Dynamic Texture Provider Example", width=300, height=300)
        with self._window.frame:
            ui.Button("Create", clicked_fn=on_click_create)

        def on_click_create():
            usd_context = omni.usd.get_context()
            stage: Usd.Stage = usd_context.get_stage()
            name = f"Thing"
            image_name = name
            prim_path = f"/World/{name}"
            # If the prim already exists, remove it so we can create it again
            try:
                stage.RemovePrim(prim_path)
                self._texture = None
            except:
                pass
            # Create the prim root
            model_root = UsdGeom.Xform.Define(stage, prim_path)
            Usd.ModelAPI(model_root).SetKind(Kind.Tokens.component)
            # Create the mesh + material + shader
            create_textured_plane_prim(stage, prim_path, image_name)
            # Open the adjacent cat.jpg file and create the texture
            dir = pathlib.Path(__file__).parent.resolve()
            image_path = dir.joinpath("cat.jpg")
            image: Image.Image = Image.open(image_path, mode='r')
            # Ensure the image format is RGBA
            image = image.convert('RGBA')
            image_bytes = image.tobytes()
            image_resolution = (image.width, image.height)
            image_format = ui.TextureFormat.RGBA8_UNORM
            self._texture = create_dynamic_texture(image_name, image_bytes, image_resolution, image_format)

    def on_shutdown(self):
        self._texture = None
