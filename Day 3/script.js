let date = document.getElementById("date"),
  day = document.getElementById("day"),
  month = document.getElementById("month"),
  year = document.getElementById("year"),
  days = [
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday"
  ],
  months = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December"
  ];

function update() {
  let now = new Date();
  date.innerText = now.getDate();
  day.innerText = days[now.getDay()];
  month.innerText = months[now.getMonth()];
  year.innerText = now.getFullYear();
}

document.body.onload = () => {
  setInterval(update, 1000);
  setTimeout(() => {
    document.getElementsByClassName("content")[0].style.height = "260px";
    document.getElementsByClassName("card")[0].style.color = "#fff";
  }, 500);
};