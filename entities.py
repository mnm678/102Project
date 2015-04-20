import point
from actions import *

class Entities(object):
   def __init__(self,name,imgs):
      self.name = name
      self.imgs = imgs
      self.current_img = 0

   def get_images(self):
      return self.imgs

   def get_image(self):
      return self.imgs[self.current_img]

   def next_image(self):
      self.current_img = (self.current_img + 1) % len(self.imgs)


class Background(Entities):
   pass


class Entity(Entities):
   def __init__(self,name,imgs,position):
      super(Entity,self).__init__(name, imgs)
      self.position = position

   def set_position(self,point):
      self.position = point

   def get_position(self):
      return self.position

   def entity_string(entity):
      try:
         return ' '.join([self._type(), entity.name, str(entity.position.x),
            str(entity.position.y), str(entity.resource_limit),
            str(entity.rate), str(entity.animation_rate)])
      except:
         return 'unknown'


class Obstacle(Entity):
   def __init__(self, name, position, imgs):
      super(Obstacle,self).__init__(name, imgs, position)

   def _type(self):
      return 'obstacle'

class PendingActions(object):
   def remove_pending_action(self, action):
      if hasattr(self, "pending_actions"):
         self.pending_actions.remove(action)

   def add_pending_action(self, action):
      if hasattr(self, "pending_actions"):
         self.pending_actions.append(action)

   def get_pending_actions(self):
      if hasattr(self, "pending_actions"):
         return self.pending_actions
      else:
         return []

   def clear_pending_actions(self):
      if hasattr(self, "pending_actions"):
         self.pending_actions = []

   def remove_entity(self, world):
      for action in self.get_pending_actions():
         world.unschedule_action(action)
      self.clear_pending_actions()
      world.remove_entity(self)


class Animated(PendingActions):
   def __init__(self, rate):
      self.rate = rate

   def get_rate(self):
      return self.rate

   def get_name(self):
      return self.name


class AnimationRate(PendingActions):
   def __init__(self,animation_rate):
      self.animation_rate = animation_rate

   def get_animation_rate(self):
      return self.animation_rate


class Miner(Entity, Animated):
   def __init__(self, name, resource_limit, position, rate, imgs,
      animation_rate):
      super(Miner,self).__init__(name, imgs, position)
      Animated.__init__(self, rate)
      self.resource_limit = resource_limit
      self.resource_count = 0
      self.animation_rate = animation_rate

   def set_resource_count(self, n):
      self.resource_count = n

   def get_resource_count(self):
      return self.resource_count

   def get_resource_limit(self):
      return self.resource_limit

   def get_animation_rate(self):
      return self.animation_rate

   def try_transform_miner(self, world, transform):
      new_entity = transform(world)
      if self != new_entity:
         clear_pending_actions(world, self)
         world.remove_entity_at(self.get_position())
         world.add_entity(new_entity)
         world.schedule_animation(new_entity)
      return new_entity

   def create_miner_action(self, world, i_store):
      def action(current_ticks):
         self.remove_pending_action(action)

         entity_pt = self.get_position()
         (tiles, found) = self._startingAction(entity_pt, world)
         
         new_entity = self
         if found:
            new_entity = self.try_transform_miner(world,
               self._returnType())

         schedule_action(world, new_entity,
            new_entity.create_miner_action(world, i_store),
            current_ticks + new_entity.get_rate())
         return tiles
      return action


class MinerNotFull(Miner):
   def __init__(self, name, resource_limit, position, rate, imgs,
      animation_rate):
      super(MinerNotFull,self).__init__(name, resource_limit, position, rate, imgs, animation_rate)
      self.pending_actions = []

   def _type(self):
      return 'miner'

   def _returnType(self):
      return self.try_transform_miner_not_full

   def miner_to_ore(self, world, ore):
      miner_pt = self.get_position()
      if not ore:
         return ([miner_pt], False)
      ore_pt = ore.get_position()
      if adjacent(miner_pt, ore_pt):
         self.set_resource_count(
            1 + self.get_resource_count())
         ore.remove_entity(world)
         return ([ore_pt], True)
      else:
         new_pt = world.next_position(miner_pt, ore_pt)
         return (world.move_entity(self, new_pt), False)

   def try_transform_miner_not_full(self, world):
      if self.resource_count < self.resource_limit:
         return self
      else:
         new_entity = entities.MinerFull(
            self.get_name(), self.get_resource_limit(),
            self.get_position(), self.get_rate(),
            self.get_images(), self.get_animation_rate())
         return new_entity

   def schedule_miner(self, world, ticks, i_store):
      schedule_action(world, self, self.create_miner_action(world, i_store),
         ticks + self.get_rate())
      world.schedule_animation(self)

   def _startingAction(self, entity_pt, world):
      ore = world.find_nearest(entity_pt, entities.Ore)
      return self.miner_to_ore(world, ore)


class MinerFull(Miner):
   def __init__(self, name, resource_limit, position, rate, imgs,
      animation_rate):
      super(MinerFull,self).__init__(name, resource_limit, position, rate, imgs, animation_rate)
      self.resource_count = resource_limit
      self.pending_actions = []

   def _returnType(self):
      return self.try_transform_miner_full

   def _startingAction(self, entity_pt,world):
      smith = world.find_nearest(entity_pt, entities.Blacksmith)
      return self.miner_to_smith(world, smith)

   def miner_to_smith(self, world, smith):
      miner_pt = self.get_position()
      if not smith:
         return ([miner_pt], False)
      smith_pt = smith.get_position()
      if adjacent(miner_pt, smith_pt):
         smith.set_resource_count(
            smith.get_resource_count() +
            self.get_resource_count())
         self.set_resource_count(0)
         return ([], True)
      else:
         new_pt = world.next_position(miner_pt, smith_pt)
         return (world.move_entity(self, new_pt), False)

   def try_transform_miner_full(self, world):
      new_entity = entities.MinerNotFull(
         self.get_name(), self.get_resource_limit(),
         self.get_position(), self.get_rate(),
         self.get_images(), self.get_animation_rate())

      return new_entity


class Vein(Entity, Animated):
   def __init__(self, name, rate, position, imgs, resource_distance=1):
      super(Vein,self).__init__(name, imgs, position)
      Animated.__init__(self, rate)
      self.resource_distance = resource_distance
      self.pending_actions = []

   def _type(self):
      return 'vein'
   
   def get_resource_distance(self):
      return self.resource_distance
   
   def create_vein_action(self, world, i_store):
      def action(current_ticks):
         self.remove_pending_action(action)
         open_pt = world.find_open_around(self.get_position(),
            self.get_resource_distance())
         if open_pt:
            ore = world.create_ore(
               "ore - " + self.get_name() + " - " + str(current_ticks),
               open_pt, current_ticks, i_store)
            world.add_entity(ore)
            tiles = [open_pt]
         else:
            tiles = []

         schedule_action(world, self,
            self.create_vein_action(world, i_store),
            current_ticks + self.get_rate())
         return tiles
      return action
   
   def schedule_vein(self, world, ticks, i_store):
      schedule_action(world, self, self.create_vein_action(world, i_store),
         ticks + self.get_rate())
   
   def create_miner_action(self, world, i_store):
      def action(current_ticks):
         self.remove_pending_action(action)

         entity_pt = self.get_position()
         ore = world.find_nearest(entity_pt, entities.Ore)
         (tiles, found) = self.miner_to_ore(world, ore)

         new_entity = self
         if found:
            new_entity = self.try_transform_miner(world,
               self.try_transform_miner_not_full)

         schedule_action(world, new_entity,
            new_entity.create_miner_action(world, i_store),
            current_ticks + new_entity.get_rate())
         return tiles
      return action


class Ore(Entity, Animated):
   def __init__(self, name, position, imgs, rate=5000):
      super(Ore,self).__init__(name, imgs, position)
      Animated.__init__(self, rate)
      self.pending_actions = []

   def _type(self):
      return 'ore'
   
   def create_ore_transform_action(self, world, i_store):
      def action(current_ticks):
         self.remove_pending_action(action)
         blob = world.create_blob(self.get_name() + " -- blob",
            self.get_position(),
            self.get_rate() // BLOB_RATE_SCALE,
            current_ticks, i_store)

         self.remove_entity(world)
         world.add_entity(blob)

         return [blob.get_position()]
      return action
   
   def schedule_ore(self, world, ticks, i_store):
      schedule_action(world, self,
         self.create_ore_transform_action(world, i_store),
         ticks + self.get_rate())
   

class Blacksmith(Entity):
   def __init__(self, name, position, imgs, resource_limit, rate,
      resource_distance=1):
      super(Blacksmith,self).__init__(name, imgs, position)
      self.resource_limit = resource_limit
      self.resource_count = 0
      self.rate = rate
      self.resource_distance = resource_distance
      self.pending_actions = []

   def _type(self):
      return 'blacksmith'
   
   def get_rate(self):
      return self.rate
   
   def get_resource_count(self):
      return self.resource_count
   
   def set_resource_count(self, n):
      self.resource_count = n


class OreBlob(Entity, AnimationRate):
   def __init__(self, name, position, rate, imgs, animation_rate):
      super(OreBlob,self).__init__(name, imgs, position)
      AnimationRate.__init__(self, animation_rate)
      self.rate = rate
      self.pending_actions = []
   
   def get_rate(self):
      return self.rate
   
   def blob_to_vein(self, world, vein):
      blob_pt = self.get_position()
      if not vein:
         return ([blob_pt], False)
      vein_pt = vein.get_position()
      if adjacent(blob_pt, vein_pt):
         vein.remove_entity(world)
         return ([vein_pt], True)
      else:
         new_pt = self.blob_next_position(world, vein_pt)
         old_entity = world.get_tile_occupant(new_pt)
         if isinstance(old_entity, Ore):
            old_entity.remove_entity(world)
         return (world.move_entity(self, new_pt), False)
   
   def create_ore_blob_action(self, world, i_store):
      def action(current_ticks):
         self.remove_pending_action(action)

         entity_pt = self.get_position()
         vein = world.find_nearest(entity_pt, entities.Vein)
         (tiles, found) = self.blob_to_vein(world, vein)

         next_time = current_ticks + self.get_rate()
         if found:
            quake = world.create_quake(tiles[0], current_ticks, i_store)
            world.add_entity(quake)
            next_time = current_ticks + self.get_rate() * 2

         schedule_action(world, self,
            self.create_ore_blob_action(world, i_store),
            next_time)

         return tiles
      return action
   
   def schedule_blob(self, world, ticks, i_store):
      schedule_action(world, self, self.create_ore_blob_action(world, i_store),
         ticks + self.get_rate())
      world.schedule_animation(self)

   def blob_next_position(self, world, dest_pt):
      horiz = sign(dest_pt.x - self.position.x)
      new_pt = point.Point(self.position.x + horiz, self.position.y)

      if horiz == 0 or (world.is_occupied(new_pt) and
         not isinstance(world.get_tile_occupant(new_pt),
         entities.Ore)):
         vert = sign(dest_pt.y - self.position.y)
         new_pt = point.Point(self.position.x, self.position.y + vert)

         if vert == 0 or (world.is_occupied(new_pt) and
            not isinstance(world.get_tile_occupant(new_pt),
            entities.Ore)):
            new_pt = point.Point(self.position.x, self.position.y)

      return new_pt


class Quake(Entity, AnimationRate):
   def __init__(self, name, position, imgs, animation_rate):
      super(Quake,self).__init__(name, imgs, position)
      AnimationRate.__init__(self, animation_rate)
      self.pending_actions = []
   
   def create_entity_death_action(self, world):
      def action(current_ticks):
         self.remove_pending_action(action)
         pt = self.get_position()
         self.remove_entity(world)
         return [pt]
      return action
   
   def schedule_quake(self, world, ticks):
      world.schedule_animation(self, QUAKE_STEPS) 
      schedule_action(world, self, self.create_entity_death_action(world),
         ticks + QUAKE_DURATION)
