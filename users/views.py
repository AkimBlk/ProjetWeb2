from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import UserRegisterForm, UserUpdateForm, ProfileUpdateForm

#pour recuperer les users et compter leurs stats
from django.contrib.auth.models import User#obliger pour faire User.objects.get(username=username) (user_profile())
from blog.models import Post#obliger pour posts = Post.objects.all() (parcourir tous les agents en db) (get_agents_stats_for_user())


# Create your views here.
#pour creer un nv user
def register(request):
    if (request.method == 'POST'):
        form = UserRegisterForm(request.POST)
        if (form.is_valid()):
            form.save()                         
            username = form.cleaned_data.get('username')
            messages.success(request, f'account created, login possible')
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'users/register.html',{'form' :form})

@login_required
def profile(request):
    if (request.method == 'POST'):
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form=ProfileUpdateForm(request.POST, 
                                 request.FILES, 
                                 instance=request.user.profile)

        if u_form.is_valid() and p_form.is_valid(): 
            u_form.save()
            p_form.save()
            messages.success(request, f'Your account has been updated')
            return redirect('profile')

    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form=ProfileUpdateForm(instance=request.user.profile)

    #recup les stats de l'user par agents.
    agents_stats = get_agents_stats_for_user(request.user.username)
    stats_per_day = []

     #donnees pour le html
    context={
        'u_form': u_form,
        'p_form': p_form,
        
        'profile_user': request.user,
        'agents_stats': agents_stats,
        'stats_per_day': stats_per_day
    }

    return render(request,'users/profile.html',context)


@login_required
def user_profile(request, username):
    try:
        profile_user = User.objects.get(username=username)
    except:
        return redirect('blog-home')
    
    #recup stats
    agents_stats = get_agents_stats_for_user(username)

    #donnees pour le html
    context={
        'profile_user': profile_user,
        'agents_stats': agents_stats,
    }
    
    return render(request, 'users/profile.html', context)

    
# fonction qui compte combien de messages un user a envoye a chaque agent
def get_agents_stats_for_user(username):
    agents_stats = []
    posts = Post.objects.all()# recupere tous les agent en db

    for post in posts:
        user_message_count = 0

         # si l'agent a un historique de conv
        if post.conversation:
            for line in post.conversation.split('|||||'):
                if ':' in line:
                    name, text = line.split(':', 1)

                    # si c'est ce le user qui a parle : +1
                    if name.strip() == username:
                        user_message_count += 1

        # ajouter aux stats seulement si le user a +1 message a l'agent
        if user_message_count > 0:
            agents_stats.append({
                'name': post.name,
                'count': user_message_count
            })

    return agents_stats
