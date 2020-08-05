LDraw Handler for Blender 2.82, written by Matthew Morrison [cuddlyogre] - cuddlyogre@gmail.com - www.cuddlyogre.com

Materials were taken almost wholesale from https://github.com/TobyLobster/ImportLDraw. I added my own glass material 
that was taken from a BlenderArtists thread, but most of it is unchanged. I essentially learned Python by dissecting 
and studying this plugin, and it inspired me to make my own. My plugin wouldn't exist without this one.

I have to write up actual instructions, but normal usage is straightforward.

Importing:
File > Import > LDraw (.mpd/.ldr/.l3b/.dat)

Exporting requires a bit of setup, but once that's taken care of:
File > Export > LDraw (.mpd/.ldr/.l3b/.dat)

I have a few parts in the official parts library that were created in Blender and exported using my plugin.

You are able to export parts and models with the correct project setup. You can even build entire models in Blender, but
the workflow needs to be figured out for that to be any kind of fun.

I built this plugin with performance and compatibility in mind. It handles MLCad parts, LDCad projects, ldr, and mpd. It 
also processes most official META commands. For instance, STEP will set keyframes so you can watch the model be built. 
Theoretically, you could build and entire animation in an MPD file if you did it right. TEXMAP support is really all 
that's missing feature wise.

https://omr.ldraw.org/files/337 loads in about 13 seconds
https://omr.ldraw.org/files/338 has lots of incorrectly written parts and MLCAD parts that import correctly 

You are able to choose the logo you want to show on studs, or no logo or stud at all.

It works with Eevee and Cycles right out of the gate.

On my TODO is the ability to replace selected parts with different resolution parts. For instances, 338 from eariler has
a lot of gaps in the tires and fender because the model is built with parts with different resolutions.

Pull requests and examples of my plugin in action are welcome.