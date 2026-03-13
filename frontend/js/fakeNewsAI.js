async function checkNews(){

let text = document.getElementById("newsInput").value

if(text.trim()===""){
alert("Please enter news text")
return
}

try{

let response = await fetch("http://127.0.0.1:5000/predict",{

method:"POST",

headers:{
"Content-Type":"application/json"
},

body:JSON.stringify({
news:text
})

})

let data = await response.json()

document.getElementById("newsResult").innerText =
"Prediction: " + data.prediction +
" | Confidence: " + data.confidence + "%"

}
catch(error){

console.error(error)

document.getElementById("newsResult").innerText =
"Error connecting to AI server"

}

}