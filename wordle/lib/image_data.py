# -*- coding: utf-8 -*-
"""Manage access to image data."""

import random


from lib.config import DATA_PATH


class ImageData(dict):
    """Manage the access to image data.

    Mapping from room id to items left for this room.

    Args:
        path (str): Path to a valid tsv file with at least
            two columns per row, containing the image/word
            pairs. Images are represented as urls.
        n (int): Number of images presented per
            participant per room (one at a time).
        game_mode: one of 'same', 'one_blind', 'different',
            specifying whether both players see the same image,
            whether they see different images, or whether one
            player is blind, i.e. does not see any image.
        shuffle (bool): Whether to randomly sample images or
            select them one by one as present in the file.
            If more images are present than required per room
            and participant, the selection is without replacement.
            Otherwise it is with replacement.
        seed (int): Use together with shuffle to
            make the image presentation process reproducible.
    """

    def __init__(self,
                 path=None,
                 n=1,
                 game_mode='same',
                 shuffle=False,
                 seed=None):
        self._path_difficult = path + "pairs-difficult.tsv"
        self._path_ideal = path + "pairs-ideal.tsv"
        self._path_easy = path + "pairs-easy.tsv"
        self._n = n
        self._mode = game_mode
        self._shuffle = shuffle

        self._images_difficult = None
        self._images_ideal = None
        self._images_easy = None
        if seed is not None:
            random.seed(seed)

        self._switch_order = self._switch_image_order()

    @property
    def n(self):
        return self._n

    @property
    def mode(self):
        return self._mode

    def get_word_image_pairs(self, room_id):
        """Create a collection of word/image pair items.

        Each item holds a word and 1 or 2 urls each to one image
        resource. The images will be loaded from there.
        For local testing, you can host the images with python:
        ```python -m SimpleHTTPServer 8000```

        This function remembers previous calls to itself,
        which makes it possible to split a file of items over
        several participants even for not random sampling.

        Args:
            room_id (str): Unique identifier of a task room.

        Returns:
            None
        """
        if self._images_difficult or self._images_ideal or self._images_easy is None:
            # first time accessing the file
            # or a new access for each random sample
            self._images_difficult = self._image_gen(self._path_difficult)
            self._images_ideal = self._image_gen(self._path_ideal)
            self._images_easy = self._image_gen(self._path_easy)

        sample = []
        while len(sample) < self._n:
            try:
                if len(sample)==0:
                    pair = random.choice(list(self._images_easy))
                if len(sample)==1:
                    pair = random.choice(list(self._images_ideal))
                if len(sample)==2:
                    pair = random.choice(list(self._images_difficult))
            except StopIteration:
                # we reached the end of the file
                # and start again from the top
                self._images_difficult = self._image_gen(self._path_difficult)
                self._images_ideal = self._image_gen(self._path_ideal)
                self._images_easy = self._image_gen(self._path_easy)
            else:
                sample.append(pair)

        print(sample)
        #if self._shuffle:
        #    # implements reservoir sampling
        #    for img_line, img in enumerate(self._images, self._n):
        #        rand_line = random.randint(0, img_line)
        #        if rand_line < self._n:
        #            sample[rand_line] = tuple(img)
        #    self._images = None

        # make sure that for the one_blind mode, the game alternates
        # between who sees the image
        if self._mode == 'one_blind':
            new_sample = []
            for item in sample:
                order = next(self._switch_order)
                if order:
                    # switch the order of images
                    new_sample.append((item[0], item[2], item[1]))
                else:
                    new_sample.append(item)
            self[room_id] = new_sample
        else:
            self[room_id] = sample

    def _image_gen(self, path):
        """Generate one image pair at a time."""
        with open(path, "r") as infile:
            for line in infile:
                data = line.strip().split("\t")
                if len(data) == 2:
                    if self.mode == 'one_blind':
                        yield data[0], data[1], None
                    elif self.mode == 'same':
                        yield data[0], data[1], data[1]
                    else:
                        raise KeyError("No second image available.")
                elif len(data) > 2:
                    if self.mode == 'one_blind':
                        yield data[0], data[1], None
                    elif self.mode == 'same':
                        yield data[0], data[1], data[1]
                    else:
                        yield data[0], data[1], data[2]

    def _switch_image_order(self):
        """For the mode one_blind, switch who sees an image"""
        last = 0
        while True:
            if last == 0:
                last = 1
            elif last == 1:
                last = 0
            yield last


if __name__ == "__main__":
    import os
    import sys
    import unittest

    im = ImageData(path=DATA_PATH, n=15, shuffle=False)
  
    im.get_word_image_pairs(22)
 
    

