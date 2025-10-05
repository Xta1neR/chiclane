// static/store/js/store.js
document.addEventListener("DOMContentLoaded", function(){
  document.querySelectorAll(".thumbnail").forEach(function(thumb){
    thumb.addEventListener("click", function(){
      const main = document.getElementById("main-image");
      main.src = this.dataset.src;
    });
  });
});
