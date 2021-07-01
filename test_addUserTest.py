# test_with_pytest.py

import unittest
import addUser

class TestAIPNaming(unittest.TestCase):

  @classmethod
  def setUpClass(self):
    #addUser.init_logger()
    print ("setup class")

  def test_add_user(self):
    print ("test")
    self.assertEqual(True, True)        

if __name__ == '__main__':
    unittest.main()