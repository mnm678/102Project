import entities
import pygame
import ordered_list
from actions import *
import occ_grid
import point
import image_store
import random

class WorldModel:
   def __init__(self, num_rows, num_cols, background):
      self.background = occ_grid.Grid(num_cols, num_rows, background)
      self.num_rows = num_rows
      self.num_cols = num_cols
      self.occupancy = occ_grid.Grid(num_cols, num_rows, None)
      self.entities = []
      self.action_queue = ordered_list.OrderedList()

   def within_bounds(self, pt):
      return (pt.x >= 0 and pt.x < self.num_cols and
         pt.y >= 0 and pt.y < self.num_rows)

   def is_occupied(self, pt):
      return (self.within_bounds(pt) and
         self.occupancy.get_cell(pt) != None)

   def find_nearest(self, pt, type):
      oftype = [(e, distance_sq(pt, e.get_position()))
         for e in self.entities if isinstance(e, type)]
      return nearest_entity(oftype)

   def add_entity(self, entity):
      pt = entity.get_position()
      if self.within_bounds(pt):
         old_entity = self.occupancy.get_cell(pt)
         if old_entity != None:
            entities.clear_pending_actions(old_entity)
         self.occupancy.set_cell(pt, entity)
         self.entities.append(entity)

   def move_entity(world, entity, pt):
      tiles = []
      if world.within_bounds(pt):
         old_pt = entity.get_position()
         world.occupancy.set_cell(old_pt, None)
         tiles.append(old_pt)
         world.occupancy.set_cell(pt, entity)
         tiles.append(pt)
         entity.set_position(pt)
      return tiles

   def remove_entity(self, entity):
      self.remove_entity_at(entity.get_position())

   def remove_entity_at(self, pt):
      if (self.within_bounds(pt) and
         self.occupancy.get_cell(pt) != None):
         entity = self.occupancy.get_cell(pt)
         entity.set_position(point.Point(-1, -1))
         self.entities.remove(entity)
         self.occupancy.set_cell(pt, None)

   def schedule_action(self, action, time):
      self.action_queue.insert(action, time)

   def unschedule_action(self, action):
      self.action_queue.remove(action)

   def update_on_time(self, ticks):
      tiles = []
      next = self.action_queue.head()
      while next and next.ord < ticks:
         self.action_queue.pop()
         tiles.extend(next.item(ticks))  # invoke action function
         next = self.action_queue.head()
      return tiles

   def get_background_image(self, pt):
      if self.within_bounds(pt):
         return self.background.get_cell(pt).get_image()

   def get_background(self, pt):
      if self.within_bounds(pt):
         return self.background.get_cell(pt)

   def set_background(self, pt, bgnd):
      if self.within_bounds(pt):
         self.background.set_cell(pt, bgnd)

   def get_tile_occupant(self, pt):
      if self.within_bounds(pt):
         return self.occupancy.get_cell(pt)

   def get_entities(self):
      return self.entities

   def next_position(self, entity_pt, dest_pt):
      horiz = sign(dest_pt.x - entity_pt.x)
      new_pt = point.Point(entity_pt.x + horiz, entity_pt.y)

      if horiz == 0 or self.is_occupied(new_pt):
         vert = sign(dest_pt.y - entity_pt.y)
         new_pt = point.Point(entity_pt.x, entity_pt.y + vert)

         if vert == 0 or self.is_occupied(new_pt):
            new_pt = point.Point(entity_pt.x, entity_pt.y)

      return new_pt

   def create_blob(self, name, pt, rate, ticks, i_store):
      blob = entities.OreBlob(name, pt, rate,
         image_store.get_images(i_store, 'blob'),
         random.randint(BLOB_ANIMATION_MIN, BLOB_ANIMATION_MAX)
         * BLOB_ANIMATION_RATE_SCALE)
      blob.schedule_blob(self, ticks, i_store)
      return blob

   def find_open_around(self, pt, distance):
      for dy in range(-distance, distance + 1):
         for dx in range(-distance, distance + 1):
            new_pt = point.Point(pt.x + dx, pt.y + dy)

            if (self.within_bounds(new_pt) and
               (not self.is_occupied(new_pt))):
               return new_pt

      return None

   def create_ore(self, name, pt, ticks, i_store):
      ore = entities.Ore(name, pt, image_store.get_images(i_store, 'ore'),
         random.randint(ORE_CORRUPT_MIN, ORE_CORRUPT_MAX))
      ore.schedule_ore(self, ticks, i_store)

      return ore

   def create_quake(self, pt, ticks, i_store):
      quake = entities.Quake("quake", pt,
         image_store.get_images(i_store, 'quake'), QUAKE_ANIMATION_RATE)
      quake.schedule_quake(self, ticks)
      return quake

   def create_vein(self, name, pt, ticks, i_store):
      vein = entities.Vein("vein" + name,
         random.randint(VEIN_RATE_MIN, VEIN_RATE_MAX),
         pt, image_store.get_images(i_store, 'vein'))
      return vein

   def create_animation_action(self, entity, repeat_count):
      def action(current_ticks):
         entity.remove_pending_action(action)

         entity.next_image()

         if repeat_count != 1:
            schedule_action(self, entity,
               self.create_animation_action(entity, max(repeat_count - 1, 0)),
               current_ticks + entity.get_animation_rate())

         return [entity.get_position()]
      return action

   def schedule_animation(self, entity, repeat_count=0):
      schedule_action(self, entity,
         self.create_animation_action(entity, repeat_count),
         entity.get_animation_rate())

   def handle_mouse_button(self, view, event, entity_select, i_store):
      mouse_pt = mouse_to_tile(event.pos, view.tile_width, view.tile_height)
      tile_view_pt = worldview.viewport_to_world(view.viewport, mouse_pt)
      if event.button == mouse_buttons.LEFT and entity_select:
         if is_background_tile(entity_select):
            worldmodel.set_background(self, tile_view_pt,
               entities.Background(entity_select,
                  image_store.get_images(i_store, entity_select)))
            return [tile_view_pt]
         else:
            new_entity = create_new_entity(tile_view_pt, entity_select, i_store)
            if new_entity:
               worldmodel.remove_entity_at(self, tile_view_pt)
               worldmodel.add_entity(self, new_entity)
               return [tile_view_pt]
      elif event.button == mouse_buttons.RIGHT:
         worldmodel.remove_entity_at(self, tile_view_pt)
         return [tile_view_pt]

      return []
      
   def save_world(self, filename):
      with open(filename, 'w') as file:
         save_load.save_world(self, file)






def nearest_entity(entity_dists):
   if len(entity_dists) > 0:
      pair = entity_dists[0]
      for other in entity_dists:
         if other[1] < pair[1]:
            pair = other
      nearest = pair[0]
   else:
      nearest = None

   return nearest


def distance_sq(p1, p2):
   return (p1.x - p2.x)**2 + (p1.y - p2.y)**2






