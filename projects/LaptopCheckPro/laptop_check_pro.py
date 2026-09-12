import sys

if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--self-test':
        from smoke_test import run
        run(sys.argv[2])
    else:
        from ui import LaptopCheckApp
        LaptopCheckApp().mainloop()
