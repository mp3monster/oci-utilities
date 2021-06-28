import unittest
import addUser

class TestAIPNaming(unittest.TestCase):


    def test_addUser(self):

      self.assertEqual(True, True)        

if __name__ == '__main__':
    addUser.init_logger()
    unittest.main()