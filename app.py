import sqlite3
import os
import click
import secrets
import hashlib
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, g, request, redirect, url_for, flash, session
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash, check_password_hash

# --- App Configuration & Helpers ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-this-key-to-something-very-secret'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
DATABASE = 'ksiega_handlowa.db'

def format_quantity(quantity):
    if not isinstance(quantity, int) or quantity <= 0:
        return "0"
    stacks = quantity // 64
    remaining = quantity % 64
    parts = []
    if stacks > 0:
        parts.append(f"{stacks}x64")
    if remaining > 0:
        parts.append(f"{remaining}")
    return " + ".join(parts)
app.jinja_env.filters['format_quantity'] = format_quantity

# --- Item List (unchanged) ---
ITEM_LIST = [
    'Acacia Sapling', 'Acacia Wood', 'Activator Rail', 'Allium', 'Amethyst Cluster', 'Amethyst Shard', 'Ancient Debris', 
    'Andesite', 'Angler Pottery Sherd', 'Anvil', 'Apple', 'Archer Pottery Sherd', 'Armadillo Scute', 'Armor Stand', 
    'Arms Up Pottery Sherd', 'Arrow', 'Arrow of Fire Resistance (01-00)', 'Arrow of Harming (Instant Damage II)', 
    'Arrow of Healing (Instant Health II)', 'Arrow of Infestation (Infested 00-22)', 'Arrow of Invisibility (01-00)', 
    'Arrow of Leaping (Jump Boost 01-00)', 'Arrow of Leaping (Jump Boost II 00-11)', 'Arrow of Night Vision (01-00)', 
    'Arrow of Oozing (00-22)', 'Arrow of Poison (00-11)', 'Arrow of Poison (Poison II 00-02)', 'Arrow of Regeneration (00-11)', 
    'Arrow of Regeneration (Regeneration II 00-02)', 'Arrow of Slow Falling (00-30)', 'Arrow of Slowness (00-30)', 
    'Arrow of Slowness (Slowness IV 00-02)', 'Arrow of Splashing', 'Arrow of Strength (01-00)', 'Arrow of Strength (Strength II 00-11)', 
    'Arrow of Swiftness (Speed 01-00)', 'Arrow of Swiftness (Speed II 00-11)', 'Arrow of Water Breathing (01-00)', 
    'Arrow of Weakness (00-30)', 'Arrow of Weaving (00-22)', 'Arrow of Wind Charging (Wind Charged 00-22)', 
    'Arrow of the Turtle Master (Slowness IV & Resistance III 00-05)', 'Arrow of the Turtle Master (Slowness VI & Resistance IV 00-02)', 
    'Awkward Lingering Potion', 'Awkward Potion', 'Awkward Splash Potion', 'Axolotl Bucket', 'Azalea', 'Azalea Leaves', 
    'Azure Bluet', 'Baked Potato', 'Bamboo', 'Bamboo Chest Raft', 'Bamboo Mosaic', 'Bamboo Mosaic Slab', 'Bamboo Mosaic Stairs', 
    'Bamboo Raft', 'Barrel', 'Basalt', 'Beacon', 'Bee Nest', 'Beehive', 'Beetroot', 'Beetroot Seeds', 'Beetroot Soup', 
    'Bell', 'Big Dripleaf', 'Birch Sapling', 'Birch Wood', 'Black Banner', 'Black Bundle', 'Black Candle', 'Black Carpet', 
    'Black Concrete', 'Black Concrete Powder', 'Black Dye', 'Black Glazed Terracotta', 'Black Stained Glass', 
    'Black Stained Glass Pane', 'Black Terracotta', 'Black Wool', 'Blackstone', 'Blackstone Slab', 'Blackstone Stairs', 
    'Blackstone Wall', 'Blade Pottery Sherd', 'Blast Furnace', 'Blaze Powder', 'Blaze Rod', 'Block of Amethyst', 
    'Block of Bamboo', 'Block of Coal', 'Block of Diamond', 'Block of Emerald', 'Block of Gold', 'Block of Iron', 
    'Block of Lapis Lazuli', 'Block of Netherite', 'Block of Quartz', 'Block of Redstone', 'Block of Resin', 
    'Block of Stripped Bamboo', 'Blue Banner', 'Blue Bundle', 'Blue Candle', 'Blue Carpet', 'Blue Concrete', 
    'Blue Concrete Powder', 'Blue Dye', 'Blue Glazed Terracotta', 'Blue Ice', 'Blue Orchid', 'Blue Stained Glass', 
    'Blue Stained Glass Pane', 'Blue Terracotta', 'Blue Wool', 'Bolt Armor Trim Smithing Template', 'Bone', 'Bone Block', 
    'Bone Meal', 'Book', 'Book and Quill', 'Bookshelf', 'Bordure Indented Banner Pattern', 'Bottle o\' Enchanting', 'Bow', 
    'Bowl', 'Brain Coral', 'Brain Coral Block', 'Brain Coral Fan', 'Bread', 'Breeze Rod', 'Brewer Pottery Sherd', 
    'Brewing Stand', 'Brick', 'Bricks', 'Brown Banner', 'Brown Bundle', 'Brown Candle', 'Brown Carpet', 'Brown Concrete', 
    'Brown Concrete Powder', 'Brown Dye', 'Brown Glazed Terracotta', 'Brown Mushroom', 'Brown Mushroom Block', 'Brown Stained Glass', 
    'Brown Stained Glass Pane', 'Brown Terracotta', 'Brown Wool', 'Brush', 'Bubble Coral', 'Bubble Coral Block', 'Bubble Coral Fan', 
    'Bucket', 'Budding Amethyst', 'Bundle', 'Burn Pottery Sherd', 'Cactus', 'Cake', 'Calcite', 'Calibrated Sculk Sensor', 
    'Campfire', 'Candle', 'Carrot', 'Carrot On A Stick', 'Cartography Table', 'Carved Pumpkin', 'Cauldron', 'Chain', 
    'Chainmail Boots', 'Chainmail Chestplate', 'Chainmail Helmet', 'Chainmail Leggings', 'Charcoal', 'Cherry Sapling', 
    'Cherry Wood', 'Chest', 'Chipped Anvil', 'Chiseled Bookshelf', 'Chiseled Deepslate', 'Chiseled Quartz Block', 
    'Chiseled Red Sandstone', 'Chiseled Sandstone', 'Chiseled Tuff', 'Chorus Flower', 'Chorus Fruit', 'Chorus Plant', 'Clay', 
    'Clay Ball', 'Clock', 'Closed Eyeblossom', 'Coal', 'Coal Ore', 'Coarse Dirt', 'Coast Armor Trim Smithing Template', 
    'Cobbled Deepslate', 'Cobbled Deepslate Slab', 'Cobbled Deepslate Stairs', 'Cobbled Deepslate Wall', 'Cobblestone', 
    'Cobblestone Slab', 'Cobblestone Stairs', 'Cobblestone Wall', 'Cobweb', 'Cocoa Beans', 'Cod Bucket', 'Compass', 
    'Composter', 'Conduit', 'Cooked Chicken', 'Cooked Cod', 'Cooked Mutton', 'Cooked Porkchop', 'Cooked Rabbit', 'Cooked Salmon', 
    'Cookie', 'Cornflower', 'Crafter', 'Crafting Table', 'Creaking Heart', 'Creeper Charge Banner Pattern', 'Creeper Head', 
    'Crimson Fungus', 'Crimson Hyphae', 'Crimson Nylium', 'Crimson Roots', 'Crimson Stem', 'Crossbow', 'Crying Obsidian', 
    'Cut Red Sandstone', 'Cut Sandstone', 'Cyan Banner', 'Cyan Bundle', 'Cyan Candle', 'Cyan Carpet', 'Cyan Concrete', 
    'Cyan Concrete Powder', 'Cyan Dye', 'Cyan Glazed Terracotta', 'Cyan Stained Glass', 'Cyan Stained Glass Pane', 'Cyan Terracotta', 
    'Cyan Wool', 'Damaged Anvil', 'Dandelion', 'Danger Pottery Sherd', 'Dark Oak Sapling', 'Dark Oak Wood', 'Dark Prismarine', 
    'Daylight Detector', 'Dead Brain Coral', 'Dead Brain Coral Block', 'Dead Brain Coral Fan', 'Dead Bubble Coral', 
    'Dead Bubble Coral Block', 'Dead Bubble Coral Fan', 'Dead Bush', 'Dead Fire Coral', 'Dead Fire Coral Block', 
    'Dead Fire Coral Fan', 'Dead Horn Coral', 'Dead Horn Coral Block', 'Dead Horn Coral Fan', 'Dead Tube Coral', 
    'Dead Tube Coral Block', 'Dead Tube Coral Fan', 'Decorated Pot', 'Deepslate', 'Deepslate Bricks', 'Deepslate Coal Ore', 
    'Deepslate Copper Ore', 'Deepslate Diamond Ore', 'Deepslate Emerald Ore', 'Deepslate Gold Ore', 'Deepslate Iron Ore', 
    'Deepslate Lapis Ore', 'Deepslate Redstone Ore', 'Deepslate Tiles', 'Detector Rail', 'Diamond', 'Diamond Axe', 'Diamond Boots', 
    'Diamond Chestplate', 'Diamond Helmet', 'Diamond Hoe', 'Diamond Horse Armor', 'Diamond Leggings', 'Diamond Ore', 'Diamond Pickaxe', 
    'Diamond Shovel', 'Diamond Sword', 'Diorite', 'Dirt', 'Disc Fragment 5', 'Dispenser', 'Dragon Egg', 'Dragon Head', 
    'Dragon\'s Breath', 'Dried Kelp', 'Dried Kelp Block', 'Dripstone Block', 'Dropper', 'Dune Armor Trim Smithing Template', 'Echo Shard', 
    'Egg', 'Emerald', 'Emerald Ore', 'Empty Map', 'Enchanted Book of Aqua Affinity', 'Enchanted Book of Bane of Arthropods I', 
    'Enchanted Book of Bane of Arthropods II', 'Enchanted Book of Bane of Arthropods III', 'Enchanted Book of Bane of Arthropods IV', 
    'Enchanted Book of Bane of Arthropods V', 'Enchanted Book of Blast Protection I', 'Enchanted Book of Blast Protection II', 
    'Enchanted Book of Blast Protection III', 'Enchanted Book of Blast Protection IV', 'Enchanted Book of Breach I', 'Enchanted Book of Breach II', 
    'Enchanted Book of Breach III', 'Enchanted Book of Breach IV', 'Enchanted Book of Channeling', 'Enchanted Book of Curse of Binding', 
    'Enchanted Book of Curse of Vanishing', 'Enchanted Book of Density I', 'Enchanted Book of Density II', 'Enchanted Book of Density III', 
    'Enchanted Book of Density IV', 'Enchanted Book of Density V', 'Enchanted Book of Depth Strider I', 'Enchanted Book of Depth Strider II', 
    'Enchanted Book of Depth Strider III', 'Enchanted Book of Efficiency I', 'Enchanted Book of Efficiency II', 'Enchanted Book of Efficiency III', 
    'Enchanted Book of Efficiency IV', 'Enchanted Book of Efficiency V', 'Enchanted Book of Feather Falling I', 'Enchanted Book of Feather Falling II', 
    'Enchanted Book of Feather Falling III', 'Enchanted Book of Feather Falling IV', 'Enchanted Book of Fire Aspect I', 
    'Enchanted Book of Fire Aspect II', 'Enchanted Book of Fire Protection I', 'Enchanted Book of Fire Protection II', 
    'Enchanted Book of Fire Protection III', 'Enchanted Book of Fire Protection IV', 'Enchanted Book of Flame', 
    'Enchanted Book of Fortune I', 'Enchanted Book of Fortune II', 'Enchanted Book of Fortune III', 'Enchanted Book of Frost Walker I', 
    'Enchanted Book of Frost Walker II', 'Enchanted Book of Impaling I', 'Enchanted Book of Impaling II', 'Enchanted Book of Impaling III', 
    'Enchanted Book of Impaling IV', 'Enchanted Book of Impaling V', 'Enchanted Book of Infinity', 'Enchanted Book of Knockback I', 
    'Enchanted Book of Knockback II', 'Enchanted Book of Looting I', 'Enchanted Book of Looting II', 'Enchanted Book of Looting III', 
    'Enchanted Book of Loyalty I', 'Enchanted Book of Loyalty II', 'Enchanted Book of Loyalty III', 'Enchanted Book of Luck of the Sea I', 
    'Enchanted Book of Luck of the Sea II', 'Enchanted Book of Luck of the Sea III', 'Enchanted Book of Lure I', 'Enchanted Book of Lure II', 
    'Enchanted Book of Lure III', 'Enchanted Book of Mending', 'Enchanted Book of Multishot', 'Enchanted Book of Piercing I', 
    'Enchanted Book of Piercing II', 'Enchanted Book of Piercing III', 'Enchanted Book of Piercing IV', 'Enchanted Book of Power I', 
    'Enchanted Book of Power II', 'Enchanted Book of Power III', 'Enchanted Book of Power IV', 'Enchanted Book of Power V', 
    'Enchanted Book of Projectile Protection I', 'Enchanted Book of Projectile Protection II', 'Enchanted Book of Projectile Protection III', 
    'Enchanted Book of Projectile Protection IV', 'Enchanted Book of Protection I', 'Enchanted Book of Protection II', 'Enchanted Book of Protection III', 
    'Enchanted Book of Protection IV', 'Enchanted Book of Punch I', 'Enchanted Book of Punch II', 'Enchanted Book of Quick Charge I', 
    'Enchanted Book of Quick Charge II', 'Enchanted Book of Quick Charge III', 'Enchanted Book of Respiration I', 'Enchanted Book of Respiration II', 
    'Enchanted Book of Respiration III', 'Enchanted Book of Riptide I', 'Enchanted Book of Riptide II', 'Enchanted Book of Riptide III', 
    'Enchanted Book of Sharpness I', 'Enchanted Book of Sharpness II', 'Enchanted Book of Sharpness III', 'Enchanted Book of Sharpness IV', 
    'Enchanted Book of Sharpness V', 'Enchanted Book of Silk Touch', 'Enchanted Book of Smite I', 'Enchanted Book of Smite II', 'Enchanted Book of Smite III', 
    'Enchanted Book of Smite IV', 'Enchanted Book of Smite V', 'Enchanted Book of Soul Speed I', 'Enchanted Book of Soul Speed II', 
    'Enchanted Book of Soul Speed III', 'Enchanted Book of Sweeping Edge I', 'Enchanted Book of Sweeping Edge II', 
    'Enchanted Book of Sweeping Edge III', 'Enchanted Book of Swift Sneak I', 'Enchanted Book of Swift Sneak II', 'Enchanted Book of Swift Sneak III', 
    'Enchanted Book of Thorns I', 'Enchanted Book of Thorns II', 'Enchanted Book of Thorns III', 'Enchanted Book of Unbreaking I', 
    'Enchanted Book of Unbreaking II', 'Enchanted Book of Unbreaking III', 'Enchanted Book of Wind Burst I', 'Enchanted Book of Wind Burst II', 
    'Enchanted Book of Wind Burst III', 'Enchanted Golden Apple', 'Enchanting Table', 'End Crystal', 'End Rod', 'End Stone', 'End Stone Bricks', 
    'Ender Chest', 'Ender Pearl', 'Explorer Pottery Sherd', 'Eye Armor Trim Smithing Template', 'Eye of Ender', 'Feather', 'Fermented Spider Eye', 
    'Fern', 'Field Masoned Banner Pattern', 'Filled Map', 'Fire Charge', 'Fire Coral', 'Fire Coral Block', 'Fire Coral Fan', 'Firework Rocket', 
    'Firework Star', 'Fishing Rod', 'Fletching Table', 'Flow Armor Trim Smithing Template', 'Flow Banner Pattern', 'Flow Pottery Sherd', 
    'Flower Charge Banner Pattern', 'Flower Pot', 'Flowering Azalea', 'Flowering Azalea Leaves', 'Friend Pottery Sherd', 'Furnace', 'Ghast Tear', 
    'Gilded Blackstone', 'Glass', 'Glass Bottle', 'Glass Pane', 'Glistering Melon Slice', 'Globe Banner Pattern', 'Glow Berries', 'Glow Ink Sac', 
    'Glow Item Frame', 'Glow Lichen', 'Glowstone', 'Glowstone Dust', 'Goat Horn (Admire)', 'Goat Horn (Call)', 'Goat Horn (Dream)', 
    'Goat Horn (Feel)', 'Goat Horn (Ponder)', 'Goat Horn (Seek)', 'Goat Horn (Sing)', 'Goat Horn (Yearn)', 'Gold Ingot', 'Gold Nugget', 
    'Gold Ore', 'Golden Apple', 'Golden Carrot', 'Golden Horse Armor', 'Granite', 'Grass Block', 'Gravel', 'Gray Banner', 'Gray Bundle', 
    'Gray Candle', 'Gray Carpet', 'Gray Concrete', 'Gray Concrete Powder', 'Gray Dye', 'Gray Glazed Terracotta', 'Gray Stained Glass', 
    'Gray Stained Glass Pane', 'Gray Terracotta', 'Gray Wool', 'Green Banner', 'Green Bundle', 'Green Candle', 'Green Carpet', 'Green Concrete', 
    'Green Concrete Powder', 'Green Dye', 'Green Glazed Terracotta', 'Green Stained Glass', 'Green Stained Glass Pane', 'Green Terracotta', 
    'Green Wool', 'Grindstone', 'Gunpowder', 'Guster Banner Pattern', 'Guster Pottery Sherd', 'Hanging Roots', 'Hay Bale', 'Heart Of The Sea', 
    'Heart Pottery Sherd', 'Heartbreak Pottery Sherd', 'Heavy Core', 'Heavy Weighted Pressure Plate', 'Honey Block', 'Honey Bottle', 
    'Honeycomb', 'Honeycomb Block', 'Hopper', 'Horn Coral', 'Horn Coral Block', 'Horn Coral Fan', 'Host Armor Trim Smithing Template', 
    'Howl Pottery Sherd', 'Ice', 'Ink Sac', 'Iron Bars', 'Iron Boots', 'Iron Chestplate', 'Iron Door', 'Iron Helmet', 'Iron Horse Armor', 
    'Iron Ingot', 'Iron Leggings', 'Iron Nugget', 'Iron Ore', 'Iron Trapdoor', 'Item Frame', 'Jack o\'Lantern', 'Jukebox', 'Jungle Sapling', 
    'Jungle Wood', 'Kelp', 'Ladder', 'Lantern', 'Lapis Lazuli', 'Lapis Ore', 'Large Amethyst Bud', 'Large Fern', 'Lava Bucket', 'Lead', 'Leather', 
    'Leather Boots', 'Leather Chestplate', 'Leather Helmet', 'Leather Horse Armor', 'Leather Leggings', 'Lectern', 'Lever', 'Light Blue Banner', 
    'Light Blue Bundle', 'Light Blue Candle', 'Light Blue Carpet', 'Light Blue Concrete', 'Light Blue Concrete Powder', 'Light Blue Dye', 
    'Light Blue Glazed Terracotta', 'Light Blue Stained Glass', 'Light Blue Stained Glass Pane', 'Light Blue Terracotta', 'Light Blue Wool', 
    'Light Gray Banner', 'Light Gray Bundle', 'Light Gray Candle', 'Light Gray Carpet', 'Light Gray Concrete', 'Light Gray Concrete Powder', 
    'Light Gray Dye', 'Light Gray Glazed Terracotta', 'Light Gray Stained Glass', 'Light Gray Stained Glass Pane', 'Light Gray Terracotta', 
    'Light Gray Wool', 'Light Weighted Pressure Plate', 'Lightning Rod', 'Lilac', 'Lily Of The Valley', 'Lily Pad', 'Lime Banner', 'Lime Bundle', 
    'Lime Candle', 'Lime Carpet', 'Lime Concrete', 'Lime Concrete Powder', 'Lime Dye', 'Lime Glazed Terracotta', 'Lime Stained Glass', 
    'Lime Stained Glass Pane', 'Lime Terracotta', 'Lime Wool', 'Lingering Potion of Fire Resistance (02-00)', 
    'Lingering Potion of Harming (Instant Damage II)', 'Lingering Potion of Healing (Instant Health II)', 'Lingering Potion of Infestation (Infested 00-45)', 
    'Lingering Potion of Invisibility (02-00)', 'Lingering Potion of Leaping (Jump Boost 02-00)', 'Lingering Potion of Leaping (Jump Boost II 00-22)', 
    'Lingering Potion of Night Vision (02-00)', 'Lingering Potion of Oozing (00-45)', 'Lingering Potion of Poison (00-22)', 
    'Lingering Potion of Poison (Poison II 00-05)', 'Lingering Potion of Regeneration (00-22)', 'Lingering Potion of Regeneration (Regeneration II 00-05)', 
    'Lingering Potion of Slow Falling (01-00)', 'Lingering Potion of Slowness (01-00)', 'Lingering Potion of Slowness (Slowness IV 00-05)', 
    'Lingering Potion of Strength (02-00)', 'Lingering Potion of Strength (Strength II 00-22)', 'Lingering Potion of Swiftness (Speed 02-00)', 
    'Lingering Potion of Swiftness (Speed II 00-22)', 'Lingering Potion of Water Breathing (02-00)', 'Lingering Potion of Weakness (01-00)', 
    'Lingering Potion of Weaving (00-45)', 'Lingering Potion of Wind Charging (Wind Charged 00-45)', 
    'Lingering Potion of the Turtle Master (Slowness IV & Resistance III 00-10)', 'Lingering Potion of the Turtle Master (Slowness VI & Resistance IV 00-05)', 
    'Lingering Water Bottle', 'Lodestone', 'Loom', 'Mace', 'Magenta Banner', 'Magenta Bundle', 'Magenta Candle', 'Magenta Carpet', 'Magenta Concrete', 
    'Magenta Concrete Powder', 'Magenta Dye', 'Magenta Glazed Terracotta', 'Magenta Stained Glass', 'Magenta Stained Glass Pane', 'Magenta Terracotta', 
    'Magenta Wool', 'Magma Block', 'Magma Cream', 'Mangrove Propagule', 'Mangrove Roots', 'Mangrove Wood', 'Medium Amethyst Bud', 'Melon', 
    'Melon Seeds', 'Melon Slice', 'Milk Bucket', 'Minecart', 'Minecart with Chest', 'Minecart with Furnace', 'Minecart with Hopper', 'Minecart with TNT', 
    'Miner Pottery Sherd', 'Moss Block', 'Moss Carpet', 'Mossy Cobblestone', 'Mossy Stone Bricks', 'Mourner Pottery Sherd', 'Mud', 'Mud Bricks', 
    'Muddy Mangrove Roots', 'Mundane Lingering Potion', 'Mundane Potion', 'Mundane Splash Potion', 'Mushroom Stem', 'Mushroom Stew', 'Music Disc 11', 
    'Music Disc 13', 'Music Disc 5', 'Music Disc Blocks', 'Music Disc Cat', 'Music Disc Chirp', 'Music Disc Creator', 'Music Disc Creator Music Box', 
    'Music Disc Far', 'Music Disc Mall', 'Music Disc Mellohi', 'Music Disc Otherside', 'Music Disc Pigstep', 'Music Disc Precipice', 'Music Disc Relic', 
    'Music Disc Stal', 'Music Disc Strad', 'Music Disc Wait', 'Music Disc Ward', 'Mycelium', 'Name Tag', 'Nautilus Shell', 'Nether Brick', 
    'Nether Bricks', 'Nether Gold Ore', 'Nether Quartz Ore', 'Nether Sprouts', 'Nether Star', 'Nether Wart', 'Nether Wart Block', 'Netherite Axe', 
    'Netherite Boots', 'Netherite Chestplate', 'Netherite Helmet', 'Netherite Hoe', 'Netherite Ingot', 'Netherite Leggings', 'Netherite Pickaxe', 
    'Netherite Scrap', 'Netherite Shovel', 'Netherite Sword', 'Netherite Upgrade Smithing Template', 'Netherrack', 'Note Block', 'Oak Sapling', 
    'Oak Wood', 'Observer', 'Obsidian', 'Ochre Froglight', 'Ominous Trial Key', 'Open Eyeblossom', 'Orange Banner', 'Orange Bundle', 'Orange Candle', 
    'Orange Carpet', 'Orange Concrete', 'Orange Concrete Powder', 'Orange Dye', 'Orange Glazed Terracotta', 'Orange Stained Glass', 'Orange Stained Glass Pane', 
    'Orange Terracotta', 'Orange Tulip', 'Orange Wool', 'Oxeye Daisy', 'Packed Ice', 'Packed Mud', 'Painting', 'Pale Hanging Moss', 'Pale Moss Block', 
    'Pale Moss Carpet', 'Pale Oak Sapling', 'Pale Oak Wood', 'Paper', 'Pearlescent Froglight', 'Peony', 'Phantom Membrane', 'Piglin Banner Pattern', 
    'Piglin Head', 'Pink Banner', 'Pink Bundle', 'Pink Candle', 'Pink Carpet', 'Pink Concrete', 'Pink Concrete Powder', 'Pink Dye', 'Pink Glazed Terracotta', 
    'Pink Petals', 'Pink Stained Glass', 'Pink Stained Glass Pane', 'Pink Terracotta', 'Pink Tulip', 'Pink Wool', 'Piston', 'Pitcher Plant', 'Pitcher Pod', 
    'Plenty Pottery Sherd', 'Podzol', 'Pointed Dripstone', 'Poisonous Potato', 'Polished Andesite', 'Polished Basalt', 'Polished Blackstone', 
    'Polished Deepslate', 'Polished Diorite', 'Polished Granite', 'Polished Tuff', 'Popped Chorus Fruit', 'Poppy', 'Potato', 
    'Potion of Fire Resistance (08-00)', 'Potion of Harming (Instant Damage II)', 'Potion of Healing (Instant Health II)', 
    'Potion of Infestation (Infested 03-00)', 'Potion of Invisibility (08-00)', 'Potion of Leaping (Jump Boost 08-00)', 
    'Potion of Leaping (Jump Boost II 01-30)', 'Potion of Night Vision (08-00)', 'Potion of Oozing (03-00)', 'Potion of Poison (01-30)', 
    'Potion of Poison (Poison II 00-21)', 'Potion of Regeneration (01-30)', 'Potion of Regeneration (Regeneration II 00-22)', 
    'Potion of Slow Falling (04-00)', 'Potion of Slowness (04-00)', 'Potion of Slowness (Slowness IV 00-20)', 'Potion of Strength (08-00)', 
    'Potion of Strength (Strength II 01-30)', 'Potion of Swiftness (Speed 08-00)', 'Potion of Swiftness (Speed II 01-30)', 
    'Potion of Water Breathing (08-00)', 'Potion of Weakness (04-00)', 'Potion of Weaving (03-00)', 'Potion of Wind Charging (Wind Charged 03-00)', 
    'Potion of the Turtle Master (Slowness IV & Resistance III 00-40)', 'Potion of the Turtle Master (Slowness VI & Resistance IV 00-20)', 
    'Powder Snow Bucket', 'Powered Rail', 'Prismarine', 'Prismarine Bricks', 'Prismarine Crystals', 'Prismarine Shard', 'Prize Pottery Sherd', 
    'Pufferfish', 'Pufferfish Bucket', 'Pumpkin', 'Pumpkin Pie', 'Pumpkin Seeds', 'Purple Banner', 'Purple Bundle', 'Purple Candle', 'Purple Carpet', 
    'Purple Concrete', 'Purple Concrete Powder', 'Purple Dye', 'Purple Glazed Terracotta', 'Purple Stained Glass', 'Purple Stained Glass Pane', 
    'Purple Terracotta', 'Purple Wool', 'Purpur Block', 'Purpur Pillar', 'Purpur Slab', 'Purpur Stairs', 'Quartz', 'Quartz Bricks', 'Quartz Pillar', 
    'Rabbit Hide', 'Rabbit Stew', 'Rabbit\'s Foot', 'Rail', 'Raiser Armor Trim Smithing Template', 'Raw Beef', 'Raw Chicken', 'Raw Cod', 'Raw Gold', 
    'Raw Iron', 'Raw Mutton', 'Raw Porkchop', 'Raw Rabbit', 'Raw Salmon', 'Recovery Compass', 'Red Banner', 'Red Bundle', 'Red Candle', 'Red Carpet', 
    'Red Concrete', 'Red Concrete Powder', 'Red Dye', 'Red Glazed Terracotta', 'Red Mushroom', 'Red Mushroom Block', 'Red Nether Bricks', 'Red Sand', 
    'Red Sandstone', 'Red Stained Glass', 'Red Stained Glass Pane', 'Red Terracotta', 'Red Tulip', 'Red Wool', 'Redstone Comparator', 'Redstone Dust', 
    'Redstone Lamp', 'Redstone Ore', 'Redstone Repeater', 'Redstone Torch', 'Reinforced Deepslate', 'Resin Brick', 'Resin Bricks', 'Resin Clump', 
    'Respawn Anchor', 'Rib Armor Trim Smithing Template', 'Rooted Dirt', 'Rose Bush', 'Rotten Flesh', 'Saddle', 'Salmon Bucket', 'Sand', 'Sandstone', 
    'Scaffolding', 'Scrape Pottery Sherd', 'Sculk', 'Sculk Catalyst', 'Sculk Sensor', 'Sculk Shrieker', 'Sculk Vein', 'Sea Lantern', 'Sea Pickle', 
    'Seagrass', 'Sentry Armor Trim Smithing Template', 'Shaper Armor Trim Smithing Template', 'Sheaf Pottery Sherd', 'Shears', 'Shelter Pottery Sherd', 
    'Shield', 'Short Grass', 'Shroomlight', 'Shulker Shell', 'Silence Armor Trim Smithing Template', 'Skeleton Skull', 'Skull Charge Banner Pattern', 
    'Skull Pottery Sherd', 'Slime Ball', 'Slime Block', 'Small Amethyst Bud', 'Small Dripleaf', 'Smithing Table', 'Smoker', 'Smooth Basalt', 
    'Smooth Quartz Block', 'Smooth Red Sandstone', 'Smooth Sandstone', 'Smooth Stone', 'Sniffer Egg', 'Snort Pottery Sherd', 'Snout Armor Trim Smithing Template', 
    'Snow', 'Snow Block', 'Snowball', 'Soul Campfire', 'Soul Lantern', 'Soul Sand', 'Soul Soil', 'Soul Torch', 'Spectral Arrow', 'Spider Eye', 
    'Spire Armor Trim Smithing Template', 'Splash Potion of Fire Resistance (08-00)', 'Splash Potion of Harming (Instant Damage II)', 
    'Splash Potion of Healing (Instant Health II)', 'Splash Potion of Infestation (Infested 03-00)', 'Splash Potion of Invisibility (08-00)', 
    'Splash Potion of Leaping (Jump Boost 08-00)', 'Splash Potion of Leaping (Jump Boost II 01-30)', 'Splash Potion of Night Vision (08-00)', 
    'Splash Potion of Oozing (03-00)', 'Splash Potion of Poison (01-30)', 'Splash Potion of Poison (Poison II 00-21)', 
    'Splash Potion of Regeneration (01-30)', 'Splash Potion of Regeneration (Regeneration II 00-22)', 'Splash Potion of Slow Falling (04-00)', 
    'Splash Potion of Slowness (04-00)', 'Splash Potion of Slowness (Slowness IV 00-20)', 'Splash Potion of Strength (08-00)', 
    'Splash Potion of Strength (Strength II 01-30)', 'Splash Potion of Swiftness (Speed 08-00)', 'Splash Potion of Swiftness (Speed II 01-30)', 
    'Splash Potion of Water Breathing (08-00)', 'Splash Potion of Weakness (04-00)', 'Splash Potion of Weaving (03-00)', 
    'Splash Potion of Wind Charging (Wind Charged 03-00)', 'Splash Potion of the Turtle Master (Slowness IV & Resistance III 00-40)', 
    'Splash Potion of the Turtle Master (Slowness VI & Resistance IV 00-20)', 'Splash Water Bottle', 'Sponge', 'Spore Blossom', 'Spruce Sapling', 
    'Spruce Wood', 'Spyglass', 'Steak', 'Stick', 'Sticky Piston', 'Stone', 'Stone Bricks', 'Stone Button', 'Stone Pressure Plate', 'Stonecutter', 
    'String', 'Stripped Acacia Log', 'Stripped Acacia Wood', 'Stripped Birch Log', 'Stripped Birch Wood', 'Stripped Cherry Log', 'Stripped Cherry Wood', 
    'Stripped Crimson Hyphae', 'Stripped Crimson Stem', 'Stripped Dark Oak Log', 'Stripped Dark Oak Wood', 'Stripped Jungle Log', 'Stripped Jungle Wood', 
    'Stripped Mangrove Log', 'Stripped Mangrove Wood', 'Stripped Oak Log', 'Stripped Oak Wood', 'Stripped Pale Oak Log', 'Stripped Pale Oak Wood', 
    'Stripped Spruce Log', 'Stripped Spruce Wood', 'Stripped Warped Hyphae', 'Stripped Warped Stem', 'Sugar', 'Sugar Cane', 'Sunflower', 
    'Suspicious Gravel', 'Suspicious Sand', 'Suspicious Stew', 'Sweet Berries', 'TNT', 'Tadpole Bucket', 'Tall Grass', 'Target', 'Terracotta', 
    'Thick Lingering Potion', 'Thick Potion', 'Thick Splash Potion', 'Thing Banner Pattern', 'Tide Armor Trim Smithing Template', 'Tinted Glass', 
    'Tipped Arrow', 'Torch', 'Torchflower', 'Torchflower Seeds', 'Totem Of Undying', 'Trapped Chest', 'Trial Key', 'Trident', 'Tripwire Hook', 
    'Tropical Fish', 'Tropical Fish Bucket', 'Tube Coral', 'Tube Coral Block', 'Tube Coral Fan', 'Tuff', 'Tuff Bricks', 'Tuff Slab', 'Tuff Stairs', 
    'Tuff Wall', 'Turtle Egg', 'Turtle Scute', 'Turtle Shell', 'Twisting Vines', 'Unwaxed Block of Copper', 'Unwaxed Exposed Copper', 
    'Unwaxed Oxidized Copper', 'Verdant Froglight', 'Vex Armor Trim Smithing Template', 'Vine', 'Ward Armor Trim Smithing Template', 'Warped Fungus', 
    'Warped Fungus On A Stick', 'Warped Hyphae', 'Warped Nylium', 'Warped Roots', 'Warped Stem', 'Warped Wart Block', 'Water Bottle', 'Water Bucket', 
    'Waxed Block of Copper', 'Waxed Exposed Copper', 'Waxed Oxidized Copper', 'Wayfinder Armor Trim Smithing Template', 'Weeping Vines', 'Wet Sponge', 
    'Wheat', 'Wheat Seeds', 'White Banner', 'White Bundle', 'White Candle', 'White Carpet', 'White Concrete', 'White Concrete Powder', 'White Dye', 
    'White Glazed Terracotta', 'White Stained Glass', 'White Stained Glass Pane', 'White Terracotta', 'White Tulip', 'White Wool', 
    'Wild Armor Trim Smithing Template', 'Wind Charge', 'Wither Rose', 'Wither Skeleton Skull', 'Wolf Armor', 'Written Book', 'Yellow Banner', 
    'Yellow Bundle', 'Yellow Candle', 'Yellow Carpet', 'Yellow Concrete', 'Yellow Concrete Powder', 'Yellow Dye', 'Yellow Glazed Terracotta', 
    'Yellow Stained Glass', 'Yellow Stained Glass Pane', 'Yellow Terracotta', 'Yellow Wool', 'Zombie Head'
]


# --- Categorization & DB Logic ---
def get_category(item_name):
    name_lower = item_name.lower()
    if 'wood' in name_lower or 'log' in name_lower or 'hyphae' in name_lower or 'stem' in name_lower: return 'Wood & Logs'
    if 'concrete' in name_lower: return 'Concrete'
    if 'wool' in name_lower: return 'Wool'
    if 'terracotta' in name_lower: return 'Terracotta'
    if 'banner' in name_lower: return 'Banners'
    if 'carpet' in name_lower: return 'Carpets'
    if 'glass' in name_lower: return 'Glass'
    if 'dye' in name_lower: return 'Dyes'
    if 'potion' in name_lower or 'arrow of' in name_lower or 'tipped arrow' in name_lower: return 'Potions & Arrows'
    if 'sword' in name_lower or 'axe' in name_lower or 'pickaxe' in name_lower or 'shovel' in name_lower or 'hoe' in name_lower: return 'Tools'
    if 'helmet' in name_lower or 'chestplate' in name_lower or 'leggings' in name_lower or 'boots' in name_lower or 'horse armor' in name_lower or 'wolf armor' in name_lower: return 'Armor'
    if 'ore' in name_lower or 'raw' in name_lower or 'ingot' in name_lower or 'shard' in name_lower or 'diamond' in name_lower or 'emerald' in name_lower or 'lapis' in name_lower or 'redstone' in name_lower or 'quartz' in name_lower or 'coal' in name_lower: return 'Ores & Minerals'
    if 'sapling' in name_lower or 'leaves' in name_lower or 'flower' in name_lower or 'mushroom' in name_lower or 'vines' in name_lower or 'roots' in name_lower or 'grass' in name_lower: return 'Plants & Fungi'
    if 'seeds' in name_lower or 'potato' in name_lower or 'carrot' in name_lower or 'apple' in name_lower or 'melon' in name_lower or 'cookie' in name_lower or 'beef' in name_lower or 'porkchop' in name_lower or 'chicken' in name_lower or 'cod' in name_lower or 'salmon' in name_lower or 'mutton' in name_lower: return 'Food'
    if 'stone' in name_lower or 'sandstone' in name_lower or 'brick' in name_lower or 'cobblestone' in name_lower or 'diorite' in name_lower or 'andesite' in name_lower or 'granite' in name_lower or 'deepslate' in name_lower or 'blackstone' in name_lower: return 'Building Blocks (Stone)'
    if 'planks' in name_lower or 'slab' in name_lower or 'stairs' in name_lower or 'fence' in name_lower or 'door' in name_lower or 'trapdoor' in name_lower: return 'Building Blocks (Wood)'
    if 'rail' in name_lower or 'minecart' in name_lower: return 'Railways'
    if 'pottery sherd' in name_lower: return 'Pottery Sherds'
    if 'armor trim' in name_lower: return 'Armor Trims'
    if 'music disc' in name_lower: return 'Music Discs'
    return 'Miscellaneous'
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
    return g.db
@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None: db.close()
def init_db():
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    for item_name in ITEM_LIST:
        category = get_category(item_name)
        db.execute('INSERT OR IGNORE INTO "Item" (name, category) VALUES (?, ?)', (item_name, category))
    try:
        admin_nick = 'Hartkoreczek'
        admin_password = 'admin'
        db.execute("INSERT INTO \"User\" (username, role, password_hash) VALUES (?, ?, ?)", 
                   (admin_nick, 'admin', generate_password_hash(admin_password)))
        print(f"Admin '{admin_nick}' has been added with default password 'admin'.")
    except db.IntegrityError: 
        print(f"Admin '{admin_nick}' already exists.")
        pass
    db.commit()
@click.command('init-db')
@with_appcontext
def init_db_command():
    init_db()
    click.echo('Initialized the database.')
app.cli.add_command(init_db_command)

# --- User & Security System ---
@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    g.user = get_db().execute('SELECT * FROM "User" WHERE id = ?', (user_id,)).fetchone() if user_id else None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None: return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.user or g.user['role'] != 'admin':
            flash("Permission denied. This page is for administrators only.", "danger")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---
@app.route('/login', methods=('GET', 'POST'))
def login():
    if g.user: return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        user = db.execute('SELECT * FROM "User" WHERE username = ?', (username,)).fetchone()
        error = None
        if user is None or not check_password_hash(user['password_hash'], password):
            error = 'Invalid username or password.'
        if error is None:
            session.clear()
            session['user_id'] = user['id']
            session.permanent = True
            flash(f"Welcome, {user['username']}! You have been logged in.", "success")
            return redirect(url_for('dashboard'))
        flash(error, "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    search_query = request.args.get('search', '')
    category_filter = request.args.get('category_filter', '')
    query = 'SELECT * FROM "Item" WHERE name LIKE ?'
    params = [f'%{search_query}%']
    if category_filter:
        query += ' AND category = ?'
        params.append(category_filter)
    query += ' ORDER BY name'
    items = db.execute(query, params).fetchall()
    categories = db.execute('SELECT DISTINCT category FROM "Item" ORDER BY category').fetchall()
    return render_template('dashboard.html', items=items, categories=categories)

@app.route('/map')
@login_required
def store_map():
    db = get_db()
    layout_cells = db.execute('SELECT * FROM "LayoutCell"').fetchall()
    cells = {(cell['x_coord'], cell['y_coord']): cell for cell in layout_cells}
    categories = db.execute('SELECT DISTINCT category FROM "Item" ORDER BY category').fetchall()
    category_colors = {cat['category']: f"#{hashlib.md5(cat['category'].encode()).hexdigest()[:6]}" for cat in categories}
    return render_template('store_map.html', cells=cells, category_colors=category_colors, grid_cols=16, grid_rows=9)

@app.route('/edit_layout', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_layout():
    db = get_db()
    if request.method == 'POST':
        db.execute('DELETE FROM "LayoutCell"')
        for key, value in request.form.items():
            if key.startswith('cell_') and value:
                _, x, y = key.split('_')
                db.execute('INSERT INTO "LayoutCell" (x_coord, y_coord, category_name) VALUES (?, ?, ?)',
                           (int(x), int(y), value))
        db.commit()
        flash("Store layout has been saved!", "success")
        return redirect(url_for('store_map'))
    layout_cells = db.execute('SELECT * FROM "LayoutCell"').fetchall()
    cells = {(cell['x_coord'], cell['y_coord']): cell for cell in layout_cells}
    categories = db.execute('SELECT DISTINCT category FROM "Item" ORDER BY category').fetchall()
    category_colors = {cat['category']: f"#{hashlib.md5(cat['category'].encode()).hexdigest()[:6]}" for cat in categories}
    return render_template('edit_layout.html', cells=cells, category_colors=category_colors, grid_cols=16, grid_rows=9)

@app.route('/edit/<int:item_id>', methods=('GET', 'POST'))
@login_required
def edit_item(item_id):
    db = get_db()
    item = db.execute('SELECT * FROM "Item" WHERE id = ?', (item_id,)).fetchone()
    if not item:
        flash("Item not found.", "danger")
        return redirect(url_for('dashboard'))
    if request.method == 'POST' and 'price' in request.form:
        if g.user['role'] != 'admin':
            flash("Only admins can change prices and master stock.", "danger")
            return redirect(url_for('edit_item', item_id=item_id))
        new_quantity = int(request.form['quantity'])
        new_price = float(request.form['price'])
        new_price_quantity = int(request.form['price_quantity'])
        changes = []
        if item['quantity'] != new_quantity:
            changes.append(f"stock from {item['quantity']} to {new_quantity}")
        if float(item['price']) != new_price:
            changes.append(f"price from {item['price']:.2f} to {new_price:.2f}")
        if item['price_quantity'] != new_price_quantity:
            changes.append(f"price-per from {item['price_quantity']} to {new_price_quantity}")
        if changes:
            change_description = f"Changed {', '.join(changes)} for item '{item['name']}'."
            db.execute('INSERT INTO "ChangeLog" (user_id, item_id, change_description) VALUES (?, ?, ?)',
                       (g.user['id'], item_id, change_description))
        db.execute('UPDATE "Item" SET quantity = ?, price = ?, price_quantity = ? WHERE id = ?',
                   (new_quantity, new_price, new_price_quantity, item_id))
        db.commit()
        flash(f"Item data for '{item['name']}' has been updated!", "success")
        return redirect(url_for('edit_item', item_id=item_id))
    suppliers = db.execute('SELECT id, username FROM "User" WHERE role IN (?, ?)', ('admin', 'supplier')).fetchall()
    return render_template('edit_item.html', item=item, suppliers=suppliers)

@app.route('/users')
@login_required
@admin_required
def manage_users():
    users = get_db().execute('SELECT * FROM "User" ORDER BY username').fetchall()
    return render_template('manage_users.html', users=users)

@app.route('/users/add', methods=['POST'])
@login_required
@admin_required
def add_user():
    username = request.form['username']
    role = request.form['role']
    password = request.form['password']
    db = get_db()
    if not password:
        flash("Password cannot be empty.", "danger")
        return redirect(url_for('manage_users'))
    try:
        db.execute('INSERT INTO "User" (username, role, password_hash) VALUES (?, ?, ?)', 
                   (username, role, generate_password_hash(password)))
        db.commit()
        flash(f"User '{username}' has been added.", "success")
    except db.IntegrityError:
        flash(f"A user with the nickname '{username}' already exists.", "danger")
    return redirect(url_for('manage_users'))

@app.route('/users/set_password/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def set_password(user_id):
    password = request.form['password']
    if not password:
        flash("Password cannot be empty.", "danger")
        return redirect(url_for('manage_users'))
    db = get_db()
    db.execute('UPDATE "User" SET password_hash = ? WHERE id = ?', 
               (generate_password_hash(password), user_id))
    db.commit()
    flash(f"Password for user has been updated.", "success")
    return redirect(url_for('manage_users'))

@app.route('/transaction/add/<int:item_id>', methods=['POST'])
@login_required
def add_transaction(item_id):
    if g.user['role'] not in ['admin', 'supplier']:
        flash("You do not have permission to register deliveries.", "danger")
        return redirect(url_for('dashboard'))
    db = get_db()
    item = db.execute('SELECT * FROM "Item" WHERE id = ?', (item_id,)).fetchone()
    if not item:
        flash("Item not found.", "danger")
        return redirect(url_for('dashboard'))
    try:
        stacks = int(request.form.get('stacks', 0) or 0)
        items_single = int(request.form.get('items_single', 0) or 0)
        quantity_supplied = (stacks * 64) + items_single
        cost = float(request.form['cost'])
        if quantity_supplied <= 0:
            raise ValueError
    except (ValueError, TypeError):
        flash("Invalid quantity or cost provided.", "danger")
        return redirect(url_for('edit_item', item_id=item_id))
    supplier_id = request.form.get('supplier_id', g.user['id'])
    db.execute('INSERT INTO "Transaction" (item_id, supplier_id, quantity_supplied, cost) VALUES (?, ?, ?, ?)',
               (item_id, supplier_id, quantity_supplied, cost))
    db.execute('UPDATE "Item" SET quantity = quantity + ? WHERE id = ?', (quantity_supplied, item_id))
    db.commit()
    flash(f"Delivery of {quantity_supplied} x '{item['name']}' has been registered.", "success")
    return redirect(url_for('edit_item', item_id=item_id))

@app.route('/transactions')
@login_required
def view_transactions():
    db = get_db()
    date_filter_str = request.args.get('date_filter')
    query = "SELECT t.timestamp, t.quantity_supplied, t.cost, i.name as item_name, u.username as supplier_username FROM \"Transaction\" t JOIN \"Item\" i ON t.item_id = i.id JOIN \"User\" u ON t.supplier_id = u.id"
    params = []
    if g.user['role'] == 'supplier':
        query += " WHERE t.supplier_id = ?"
        params.append(g.user['id'])
    if g.user['role'] == 'admin' and date_filter_str:
        query += " WHERE date(t.timestamp) = ?"
        params.append(date_filter_str)
    query += " ORDER BY t.timestamp DESC"
    transactions = db.execute(query, params).fetchall()
    summary = None
    if g.user['role'] == 'admin' and date_filter_str:
        summary_query = "SELECT u.username, SUM(t.cost) as total_cost FROM \"Transaction\" t JOIN \"User\" u ON t.supplier_id = u.id WHERE date(t.timestamp) = ? GROUP BY u.username ORDER BY total_cost DESC"
        summary = db.execute(summary_query, [date_filter_str]).fetchall()
    return render_template('transactions.html', transactions=transactions, summary=summary)

@app.route('/changelog')
@login_required
def view_changelog():
    db = get_db()
    query = "SELECT cl.timestamp, cl.change_description, u.username FROM \"ChangeLog\" cl JOIN \"User\" u ON cl.user_id = u.id"
    params = []
    if g.user['role'] != 'admin':
        query += " WHERE cl.user_id = ?"
        params.append(g.user['id'])
    query += " ORDER BY cl.timestamp DESC"
    logs = db.execute(query, params).fetchall()
    return render_template('changelog.html', logs=logs)

@app.route('/order', methods=['GET', 'POST'])
@login_required
def place_order():
    db = get_db()
    if request.method == 'POST':
        item_id = request.form.get('item_id')
        notes = request.form.get('notes', '')
        try:
            double_chests = int(request.form.get('double_chests', 0) or 0)
            stacks = int(request.form.get('stacks', 0) or 0)
            items_single = int(request.form.get('items_single', 0) or 0)
            quantity = (double_chests * 54 * 64) + (stacks * 64) + items_single
            if not item_id or quantity <= 0:
                raise ValueError
        except (ValueError, TypeError):
            flash("You must select an item and provide a valid quantity.", "danger")
            return redirect(url_for('place_order'))
        db.execute(
            'INSERT INTO "Orders" (user_id, item_id, quantity_requested, notes) VALUES (?, ?, ?, ?)',
            (g.user['id'], item_id, quantity, notes)
        )
        db.commit()
        flash("Your order has been placed successfully!", "success")
        return redirect(url_for('dashboard'))
    items = db.execute('SELECT id, name, category, quantity FROM "Item" ORDER BY name').fetchall()
    categories = db.execute('SELECT DISTINCT category FROM "Item" ORDER BY category').fetchall()
    return render_template('place_order.html', items=items, categories=categories)

@app.route('/orders')
@login_required
@admin_required
def view_orders():
    status_filter = request.args.get('status', 'pending')
    db = get_db()
    orders = db.execute("""
        SELECT o.id, o.created_at, o.quantity_requested, o.status, i.name as item_name, u.username
        FROM "Orders" o JOIN "Item" i ON o.item_id = i.id JOIN "User" u ON o.user_id = u.id
        WHERE o.status = ? ORDER BY o.created_at DESC
    """, (status_filter,)).fetchall()
    return render_template('view_orders.html', orders=orders, status_filter=status_filter)

@app.route('/order/update/<int:order_id>/<string:status>', methods=['POST'])
@login_required
@admin_required
def update_order_status(order_id, status):
    if status not in ['completed', 'cancelled']:
        flash("Invalid status.", "danger")
        return redirect(url_for('view_orders'))
    db = get_db()
    db.execute('UPDATE "Orders" SET status = ? WHERE id = ?', (status, order_id))
    db.commit()
    flash(f"Order #{order_id} has been marked as {status}.", "success")
    return redirect(url_for('view_orders'))

if __name__ == '__main__':
    app.run(debug=True, port=8000)