
class dict_class(dict):
    def __init__(self):
        self.roots = []

    def add_dir(self, dir, img_dir):
        self.__setitem__(dir, img_dir)

    
    def __repr__(self):
        return str(self.__len__())

    def get_root(self, root):
        print(self.__getitem__(root))


if __name__ == "__main__":

    x = dict_class()

    x.add_dir("test", 1)

    print(x)

    x.get_root('test')
