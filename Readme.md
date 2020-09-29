LDraw Handler for Blender 2.82+, written by Matthew Morrison [cuddlyogre] - cuddlyogre@gmail.com - www.cuddlyogre.com

Materials were taken almost wholesale from https://github.com/TobyLobster/ImportLDraw. I added my own glass material 
that was taken from a BlenderArtists thread, but most of it is unchanged. I essentially learned Python by dissecting 
and studying this plugin, and it inspired me to make my own. This plugin wouldn't exist without this one.

I built this plugin with performance and compatibility in mind.  

https://omr.ldraw.org/files/337 loads in about 13 seconds
https://omr.ldraw.org/files/338 has lots of incorrectly written parts and MLCad parts that import correctly 

It handles MLCad parts, LDCad projects, ldr, and mpd. It also processes most official META commands. For 
instance, STEP will set keyframes so you can watch the model be built. Theoretically, you could build 
an entire animation in an MPD file if you did it right. LeoCAD and LDCad groups are supported. LeoCAD cameras are 
supported as well. If you have LSynth parts installed, it will import those as well.

BFC meta commands aren't parsed at all. I chose to rely on recalculate normals to handle face normals.

You are able to choose the logo you want to show on studs, or no logo or stud at all.

It works with Eevee and Cycles right out of the gate.

TEXMAP support is really all that's missing spec wise. It's very complicated and I welcome any help you can give.

The ability to replace selected parts with different resolution parts is on my TODO list. For instances, 
338 from earlier has a lot of gaps in the tires and fender because the model is built with parts with different 
resolutions. 

__**Importing:** File > Import > LDraw (.mpd/.ldr/.l3b/.dat)__  

**Ldraw filepath:** The path to your Ldraw folder. On Windows, the plugins searches the roots of A:-Z:
for an Ldraw folder (C:\ldraw). On Linux, it searches the home folder for an ldraw folder (~/ldraw).
I don't have a Mac to test on, so on Mac OS, this value will be blank.  

**Import Options**  

**Use alternate colors:** Uses LDCfgalt.ldr for more accurate colors.  
**Part resolution:** The quality of parts to use. Low resolution is quicker to import, but doesn't look
as good. High resolution looks better but take longer to import.  
**Display logo:** Display the logo on the stud.  
**Chosen logo:** Which logo to display. logo and logo2 aren't used and are only included for completeness.  

**Scaling Options**  

**Import scale:** What scale to import at. Full scale is 1.0 and is so huge that it is
unwieldy in the viewport.  
**Parent to empty:** Parent the imported model to an empty to make it easier to manipulate.  
**Make gaps:** Make small gaps between bricks. A small gap is more realistic.  
**Gap scale:** Scale individual parts by this much to create the gap.  
**Gap target:** Whether to scale the object data or mesh data.  
**Gap strategy:** If object then the gap is applied to the object directly.
If constraint, an empty named gap_scale can be scaled to adjust to gaps between parts.  

**Cleanup Options**  

**Remove doubles:** Merge vertices that are within a certain distance.  
**Merge distance:** How close the vertices have to be to merge them.  
**Smooth type:** Use either autosmooth or an edge split modifier to smooth part faces.  
**Shade smooth:**  Use flat or smooth shading for part faces.  
**Recalculate normals:** Recalculate normals during import to ensure all normals face outside.  

**Meta Commands** - Process LDraw META commands.  

**GROUP:** Imports LeoCAD and LDCad groups.  
**PRINT/WRITE:** Prints PRINT/WRITE META commands to the system console.  
**STEP:** Adds a keyframe that shows the part at the moment in the timeline.  
**Frames per step:** How many frames to put between keyframes.  
**Set step end frame:** Set the final STEP keyframe.  
**CLEAR:** Hides all parts at before this point of the timeline.  
**SAVE:** Doesn't do anything.  
**Set timeline markers:** Add markers to the timeline where META commands were encountered.  

**Extras**  

**Prefer unofficial parts:** If a part is in both the unofficial and official library, use the unofficial one.  
**Import all materials:** Import all LDraw materials, not just the ones used by the model.  
**Add subsurface:** Attach a subsurface shader node to materials.  
**Bevel edges:** Bevel part edges slightly. This might cause some parts to look incorrect.  
**Debug text:** Render debug text to the system console.  
**No studs:** Don't import studs. Not particularly useful but is neat to see.  
**Import edges:** Import LDraw edges as edges.  
**Import edges as grease pencil:** Import LDraw edges as grease pencil lines.  

__**Exporting:** File > Export > LDraw (.mpd/.ldr/.l3b/.dat)__  
  
**Ldraw filepath:**  Same as above. Used for validating color codes.  

**Export Options**  

**Selection only:** Only export selected objects.  
**Use alternate colors:** Same as above. Used for validating color codes.  
**Export precision:** How many vertex position decimal points to keep.
2 is sufficient for almost everything.  

**Cleanup Options**  

**Remove doubles:** Same as above. Helps minimize file size.  
**Merge distance:** Same as above.  
**Recalculate normals:** Use Blender to determine face winding instead of having to deal with BFC.  
**Triangulate mesh:** Triangulate the mesh. Turns quads and ngons into tris.  
**Ngon handling:** If there is an ngon, what to do with it. Skip ignores any ngons.
Triangulate splits them into triangles.  

Exporting a part is as easy as File > Export. But exporting a part properly requires a bit of setup, 
but once that's taken care of it works well. Exported faces are sorted by color code then by line type. A proper
tutorial is on my TODO list.

I have a few parts in the official parts library that were created in Blender and exported using this plugin.

You are able to export parts and models with the correct project setup. You can even build 
entire models in Blender, but the workflow needs to be figured out for that to be any kind of fun.

Pull requests and examples of this plugin in action are welcome.
