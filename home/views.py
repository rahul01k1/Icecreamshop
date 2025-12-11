from django.shortcuts import render , redirect , get_object_or_404
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.contrib.auth import login , logout 
from django.contrib.auth.hashers import make_password , check_password
from django.contrib import messages
from  .models import Buyer , Seller , Product , Cart , Wishlist , Message , Newsletter ,Order 
from django.core.files.storage import FileSystemStorage
from django.core.exceptions import ValidationError


# Navbar  Functions
def home(request):
    return render(request,"pages/home.html")

def order(request):
    if not request.session.get("user_id"):
        return redirect("login")
    
    user = Buyer.objects.get(id = request.session.get("user_id"))
    order = Order.objects.filter(user=user).order_by('-id')

    context = {
        "orders":order
    }
    return render(request,"pages/order.html",context)

def menu(request):
    products = Product.objects.all()

    paginator = Paginator(products, 12)  # 12 products per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, "pages/menu.html", {"products": page_obj})

def about(request):
    return render(request,"pages/about.html")

def contact(request):
    if request.method == "POST":
        if request.session.get('user_id'):
            buyer = Buyer.objects.get(id=request.session['user_id'])
            subject = request.POST.get("subject")
            user_messages = request.POST.get("message")

            user_message = Message(
                user=buyer,
                name=buyer.user_name,
                email=buyer.user_email,
                subject=subject,
                message=user_messages
            )
            user_message.save()
            messages.success(request, "Message Sent Successfully.")
            return redirect("contact")
        else:
            messages.error(request, "Please login to send a message.")
            return redirect("login")

    return render(request,"pages/contact.html")

# Search Product Function 
def search_product(request):
    if request.method == "POST":
        search_product = request.POST.get("search_product")  # fetch search input
        products = Product.objects.filter(product_name__icontains=search_product)  # correct filtering

        if products.exists():
            return render(request, "search/search_product.html", {
                "products": products,
                "search_product": search_product
            })
        else:
            messages.error(request, "No Product Found.")
            return render(request, "search/search_product.html", {
                "products": [],
                "search_product": search_product
            })

    return render(request, "search/search_product.html")


# Cart & Wishlist Functions 
def cart(request):
    return render(request,"shop/cart.html")

def add_to_cart(request):
    return redirect("cart")

def update_cart(request,id):
    return redirect("cart")

def remove_cart(request,id):
    return redirect("cart")

def empty_cart(request,id):
    return redirect("cart")

def checkout(request):
    return render(request,"shop/checkout.html")

def wishlist(request):
    return render(request,"shop/wishlist.html")


def toggle_wishlist(request, id):
    product = Product.objects.get(id=id)
    user = request.user

    if Wishlist.objects.filter(user=user, product=product).exists():
        Wishlist.objects.filter(user=user, product=product).delete()
        return JsonResponse({"status": "removed"})
    else:
        Wishlist.objects.create(user=user, product=product)
        return JsonResponse({"status": "added"})


def add_to_wishlist(request,id):
    return redirect("wishlist")

def remove_wishlist(request,id):
    return redirect("wishlist")

  #  Views Function 

def view_product(request,id):
    return render(request,"shop/views/view_product.html")

def view_order(request, id):
    if not request.session.get('user_id'):
        return redirect("login")

    order = get_object_or_404(Order, id=id)

    if order.user.id != request.session.get("user_id"):
        return redirect("order")

    # Correct reverse relation
    items = order.orderitem_set.select_related("product").all()

    return render(request, "view_order.html", {
        "order": order,
        "items": items,
        "grand_total": order.total_amount
    })

def cancel_order(request,id):
    if not request.session.get("user_id"):
        return redirect("login")
    
    order = get_object_or_404(Order,id=id)

    if order.user.id != request.session.get("user_id"):
        return redirect("order")
    
    for item in order.items.all():
        item.product.stock += item.qty
    return redirect("view_order")



# Profile Functions
def profile(request):
    return render(request,"user/profile.html")

def update_profile(request):
    return render(request,"user/update_profile.html")

def user_messages(request):
    return render(request,"user/messages.html")


# Authenticate Functions
def user_register(request):
    if request.method == "POST":
        username = request.POST.get('name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        cpassword = request.POST.get('cpassword')
        profile_image = request.FILES.get('profile_image')

        if password != cpassword:
            messages.error(request,"Passwords do not match!")
            return redirect("register")
        
        if Buyer.objects.filter(user_email = email).exists():
            messages.error(request,"Email Already exists!")
            return redirect("register")
         
         # Image Validation
        if profile_image:
            valid_extensions = ['jpg','jpeg','png','gif'] 
            file_extension = profile_image.name.split('.')[-1].lower()
            if file_extension not in valid_extensions:
                messages.error(request,"Invalid file format! Only JPG, JPEG, PNG and GIF allowed.")
                return redirect("register")
            
        
        user = Buyer(
            user_name = username,
            user_email = email,
            user_password = make_password(password),
            user_image = profile_image if profile_image else "user_profile.jpg"
        )
        user.save()

        request.session['user_id'] = user.id
        request.session['user_name'] = user.user_name
        request.session['user_email'] = user.user_email
        request.session['user_image'] = str(user.user_image)

        messages.success(request, f"Welcome {user.user_name}! Account created successfully.")
        return redirect("home") 
    
    return render(request,"user/auth/register.html")

def user_login(request):
    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')
        try:
            user =  Buyer.objects.get(user_email = email)
        except Buyer.DoesNotExist:
            messages.error(request,"Email not registered!")
            return redirect("login")
        
        if check_password(password, user.user_password):

            request.session['user_id'] = user.id
            request.session['user_name'] = user.user_name
            request.session['user_email'] = user.user_email
            request.session['user_image'] = str(user.user_image)

            messages.success(request,f"Welcome Back ,{user.user_name}")
            return redirect("home")
        else :
            messages.error(request, "Incorrect password!")
            return redirect("login")
            
    return render(request,"user/auth/login.html")

def user_logout(request):
    request.session.flush()
    messages.success(request,"Logout Successfully!")
    return redirect("login")


