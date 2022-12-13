def buildDB(mysql):
   
    cursor = mysql.connection.cursor()
    
    cursor.execute("CREATE TABLE customers (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(255), address VARCHAR(255))")
    mysql.connection.commit()
