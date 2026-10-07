from django.shortcuts import render, redirect
from django.views.generic import (
    ListView, 
    DetailView, 
    CreateView, 
    UpdateView,
    DeleteView,
)
from .models import Post
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required

#cooldown
from .models import PostCooldown
from django.utils import timezone
from django.contrib import messages

#helbplay
import base64
import requests

#pour IA API
import os # car clé dans le run.sh
from groq import Groq
#pour IA LOCAL
import ollama

def home(request):
    context = {
        'posts' : Post.objects.all()
    }
    return render(request, 'blog/home.html', context)

class PostListView(ListView):
    model = Post
    template_name = 'blog/home.html'
    context_object_name = 'posts'
    ordering = ['-last_message_date']#gere l'ordre d'affichage des Agent/Post

class PostDetailView(LoginRequiredMixin, DetailView):
    model = Post
    template_name = 'blog/post_detail.html'

    api_model = "llama-3.3-70b-versatile"
    local_model = "qwen2.5:0.5b"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        chat_messages = []
        raw_chat_msg = self.object.conversation

        # split la conversation db en message pour l'affichage html. apres faire msg.name ou msg.text
        for part in raw_chat_msg.split('|||||'):
            if ":" in part:
                name, text = part.split(":", 1)#1 pour split seulement le 1er :
                chat_messages.append({
                    "name": name.strip(),
                    "text": text.strip()
                })

        context["chat_messages"] = chat_messages
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        # # verif le cooldown
        interaction, created = PostCooldown.objects.get_or_create(
            post=self.object,
            user=request.user
        )

        time_spent = (timezone.now() - interaction.last_interaction).total_seconds()

        # si pas assez de temps ecoule par rapport au dernier message, on return sur la page + message d'info du temps restant
        if not created and time_spent < self.object.cooldown:
            time_remaining = int(self.object.cooldown - time_spent)
            messages.info(
                request,
                f"Veuillez attendre encore {time_remaining} seconde(s) avant de renvoyer un message."
            )
            return redirect('post-detail', pk=self.object.pk)
        #-----

        # recuperer le message epuis enlever les ||||| au cas ou le user essaye de casser la db
        user_message = request.POST.get('message', '').strip()
        user_message = user_message.replace('|||||', '')

        # prepare le message pour l'ia
        messages_list = [{"role": "system", "content": self.object.pre_prompt}]


        # faut ajouter tout l'historique de la conv pour l'ia. comme ca il sait ce qu'il c'est passer avant.
        for part in self.object.conversation.split("|||||"):
            if ":" in part:
                name, text = part.split(":", 1)#1 pour split seulement le 1er :
                name = name.strip()
                text = text.strip()

                # si c'est l'agent qui parle
                if name == self.object.name:
                    messages_list.append({
                        "role": "assistant",
                        "content": text
                    })

                # sinon c'est le user
                else:
                    messages_list.append({
                        "role": "user",
                        "content": f"{name} says: {text}"
                    })

        # ajoute le nouveau message de l'user pour envoyer le tout a l'ia
        messages_list.append({
            "role": "user",
            "content": f"{request.user.username} says: {user_message}"
        })
        
        # IA

        response_text = ""

        # API groq
        if self.object.model_type == 'API':
            try:
                client = Groq(api_key=os.environ.get('GROQ_API_KEY'))
                completion = client.chat.completions.create(
                    model=self.api_model,
                    messages=messages_list,
                    temperature=1,
                    max_completion_tokens=1024,
                    top_p=1,
                    stream=True,
                    stop=None
                )

                for chunk in completion:
                    response_text += chunk.choices[0].delta.content or ""     
            except:
                response_text = "Erreur API"
        
        else: #LOCAL ollama
            try:
                client = ollama
                completion = client.chat(
                    model=self.local_model,
                    messages=messages_list,
                    stream=True
                )
                
                for chunk in completion:
                    response_text += chunk['message']['content']
            except:
                response_text = "Erreur Ollama"
        
        #enlever les ||||| si jamais l'ia renvoye une reponses contenant ca
        response_text = response_text.replace('|||||', '')

        #sauvegarder user,msg + ia,msg dans la db
        self.object.conversation += f"{self.request.user.username}:{user_message}|||||"
        self.object.conversation += f"{self.object.name}:{response_text}|||||"
        
        self.object.interaction_count += 1
        self.object.save()
        
        #met a jout le derniere interaction car autonow=true dans le model.
        interaction.save()

        return redirect('post-detail', pk=self.object.pk)

class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    fields = ['name', 'description', 'pre_prompt', 'model_type','avatar', 'cooldown']

    def form_valid(self, form):
        form.instance.creator = self.request.user
        return super().form_valid(form)

class PostUpdateView(LoginRequiredMixin,UserPassesTestMixin, UpdateView):
    model = Post
    fields = ['name', 'description', 'pre_prompt', 'model_type','avatar', 'cooldown']

    def form_valid(self, form):
        form.instance.creator = self.request.user
        return super().form_valid(form)

    def test_func(self):
        post = self.get_object()
        if self.request.user == post.creator:
            return True
        return False

class PostDeleteView(LoginRequiredMixin,UserPassesTestMixin,DeleteView):
    model = Post
    success_url = '/'

    def test_func(self):
        post = self.get_object()
        if self.request.user == post.creator:
            return True
        return False
    
def about(request):
    return render(request, 'blog/about.html', {'title' : 'About'})

@login_required
def helbplay(request):

    key = "lcHuCbelkouacipsyQ7" 

    if request.method == 'POST':
        #recup le message et le username
        message = request.POST.get('message', '').strip()
        user = request.user.username
        
        #converti en base64
        user_bytes = user.encode("utf-8")
        message_bytes = message.encode("utf-8")
        key_bytes = key.encode("utf-8")

        base64_user_bytes = base64.b64encode(user_bytes)
        base64_message_bytes = base64.b64encode(message_bytes)
        base64_key_bytes = base64.b64encode(key_bytes)

        base64_user_string = base64_user_bytes.decode("utf-8")
        base64_message_string = base64_message_bytes.decode("utf-8")
        base64_key_string = base64_key_bytes.decode("utf-8")

        #faire 'url
        url = "https://helbplays2526.alwaysdata.net/chat.php"
        url += "?username=" + base64_user_string
        url += "&message=" + base64_message_string
        url += "&key=" + base64_key_string

        #envoyer le message avec GET
        r = requests.get(url)

        return redirect('helbplay')

    chat_messages = []

    # recuperer le chat 
    try:
        r = requests.get("https://helbplays2526.alwaysdata.net/chat.txt")
        lines = r.text.strip().splitlines()

        # split chaque ligne pour garder user et message seulement
        for line in lines:
            parts = line.split(":")

            chat_messages.append({
                "user": parts[0],
                "text": parts[1]
            })

    except Exception:
        pass

    return render(request, 'blog/helbplay.html', {'chat_messages': chat_messages})