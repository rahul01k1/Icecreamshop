from django.db import models
from decimal import Decimal


# Create your models here.

class Buyer(models.Model):
    id = models.AutoField(primary_key=True)
    user_name = models.CharField(max_length = 100)
    user_email = models.EmailField(max_length = 200,unique = True)
    user_password = models.CharField(max_length = 200)
    user_image = models.ImageField(upload_to = "profile/",default="user_profile.jpg")
    created_at = models.DateTimeField(auto_now_add = True)

    def __str__(self):
        return self.user_name


class Seller(models.Model):
    id = models.AutoField(primary_key=True)
    seller_name = models.CharField(max_length = 200)
    seller_email = models.EmailField(max_length = 200,unique = True)
    seller_password = models.CharField(max_length = 200)
    seller_image = models.ImageField(upload_to = "sellers/",default = "seller_profile.jpg")
    created_at = models.DateTimeField(auto_now_add = True)

    def __str__(self):
        return self.seller_name
    

class Product(models.Model):
    id = models.AutoField(primary_key=True)
    seller = models.ForeignKey(Seller,on_delete = models.CASCADE)
    product_name = models.CharField(max_length = 255)
    product_price = models.DecimalField(max_digits=10,decimal_places=2)
    product_image = models.ImageField(upload_to = "products/")
    product_stock = models.IntegerField()
    product_detail = models.TextField()
    product_status = models.CharField(max_length = 100)
    add_at = models.DateTimeField(auto_now_add = True)

    def __str__(self):
        return self.product_name


class Cart(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(Buyer,on_delete = models.CASCADE)
    product = models.ForeignKey(Product,on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10,decimal_places=2)
    qty = models.IntegerField(default=1)

    def subtotal(self):
        return self.price * self.qty
    
    def __str__(self):
        return f"{self.user.user_name} - {self.product.product_name}"
    

class Wishlist(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(Buyer,on_delete = models.CASCADE)
    product = models.ForeignKey(Product,on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10,decimal_places=2)

    def __str__(self):
        return f"{self.user.user_name} - {self.product.product_name}"
    


class Order(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(Buyer , on_delete = models.CASCADE)
    seller = models.ForeignKey(Seller, on_delete = models.CASCADE)
    product = models.ForeignKey(Product , on_delete = models.CASCADE)
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    number = models.CharField(max_length = 10)
    address = models.CharField(max_length=255)
    address_type = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10,decimal_places=2)
    qty = models.IntegerField()
    date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=100, default="in-Progress..")
    payment_status = models.CharField(max_length=255,default = "pending")

    def total_price(self):
        return self.price * self.qty

    def __str__(self):
        return f"Order #{self.id} - {self.user.user_name}"
    

class Message(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(Buyer,on_delete= models.CASCADE)
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=100)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.user_name} - {self.subject}"


class Newsletter(models.Model):
    email = models.EmailField(max_length=255,unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email



